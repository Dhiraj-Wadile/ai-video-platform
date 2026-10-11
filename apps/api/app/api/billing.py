import hashlib
import hmac
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services import billing_service

logger = logging.getLogger(__name__)

router = APIRouter()


class CheckoutRequest(BaseModel):
    plan: str = Field(..., max_length=20)
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class UpgradeRequest(BaseModel):
    plan: str = Field(..., max_length=20)


@router.get("/plans")
async def list_plans(user: User = Depends(get_current_user)):
    return {
        "plans": billing_service.plan_catalog(),
        "current_plan": getattr(user, "plan", None) or billing_service.DEFAULT_PLAN,
        "stripe_configured": billing_service.stripe_configured(),
    }


@router.get("/usage")
async def get_usage(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await billing_service.usage_summary(db, user)


@router.post("/checkout")
async def checkout(
    request: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not billing_service.is_valid_plan(request.plan):
        raise HTTPException(status_code=422, detail=f"Unknown plan: {request.plan}")
    if request.plan == billing_service.DEFAULT_PLAN:
        raise HTTPException(status_code=400, detail="The Free plan does not require checkout")

    success = request.success_url or "http://localhost:3000/billing/success"
    cancel = request.cancel_url or "http://localhost:3000/pricing"

    try:
        session = await billing_service.create_checkout_session(user, request.plan, success, cancel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # No Stripe key -> demo mode. Apply the change immediately so the flow is usable.
    if session.get("mode") == "demo":
        await billing_service.apply_plan(db, user, request.plan)
        await db.commit()
        session["applied"] = True

    return session


@router.post("/upgrade")
async def upgrade(
    request: UpgradeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Directly set the plan. Only allowed when Stripe is not configured (demo mode);
    with Stripe live, plan changes must come through a paid checkout/webhook."""
    if billing_service.stripe_configured():
        raise HTTPException(
            status_code=403,
            detail="Billing is live. Upgrade through /api/billing/checkout so payment is collected.",
        )
    if not billing_service.is_valid_plan(request.plan):
        raise HTTPException(status_code=422, detail=f"Unknown plan: {request.plan}")
    await billing_service.apply_plan(db, user, request.plan)
    await db.commit()
    return {"plan": user.plan}


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    try:
        parts = dict(p.split("=", 1) for p in sig_header.split(","))
        timestamp = parts["t"]
        signature = parts["v1"]
    except (ValueError, KeyError):
        return False
    signed = f"{timestamp}.{payload.decode()}"
    expected = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()

    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook secret is not configured")

    sig_header = request.headers.get("stripe-signature", "")
    if not _verify_stripe_signature(payload, sig_header, settings.stripe_webhook_secret):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if event.get("type") == "checkout.session.completed":
        obj = event.get("data", {}).get("object", {})
        metadata = obj.get("metadata", {}) or {}
        user_id = metadata.get("user_id")
        plan_id = metadata.get("plan")
        if user_id and plan_id and billing_service.is_valid_plan(plan_id):
            user = (
                await db.execute(select(User).where(User.id == user_id))
            ).scalar_one_or_none()
            if user:
                await billing_service.apply_plan(db, user, plan_id, obj.get("customer"))
                await db.commit()
            else:
                logger.warning("Stripe webhook references unknown user %s", user_id)

    # Always 200 so Stripe stops retrying events we don't act on.
    return {"received": True}
