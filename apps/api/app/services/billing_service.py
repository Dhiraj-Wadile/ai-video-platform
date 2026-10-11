"""Subscription plans, usage metering and Stripe checkout.

Plans are plain data so a deployment can retune limits without a migration. Usage is
counted from real rows (render jobs this calendar month), so it is always accurate and
never needs a background job to reset.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.job import RenderJob
from app.models.project import Project
from app.models.user import User

logger = logging.getLogger(__name__)

UNLIMITED = -1

# Ordered cheapest -> most expensive. `order` controls the upgrade path.
PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "id": "free",
        "name": "Free",
        "price_cents": 0,
        "videos_per_month": 3,
        "max_resolution": "720p",
        "watermark": True,
        "scheduling": False,
        "api_access": False,
        "blurb": "Try the full pipeline with up to 3 videos a month.",
    },
    "creator": {
        "id": "creator",
        "name": "Creator",
        "price_cents": 1900,
        "videos_per_month": 30,
        "max_resolution": "1080p",
        "watermark": False,
        "scheduling": True,
        "api_access": False,
        "blurb": "For solo creators shipping content every week.",
    },
    "studio": {
        "id": "studio",
        "name": "Studio",
        "price_cents": 4900,
        "videos_per_month": UNLIMITED,
        "max_resolution": "4K",
        "watermark": False,
        "scheduling": True,
        "api_access": True,
        "blurb": "Unlimited videos, 4K and API access for teams.",
    },
}

PLAN_ORDER = ["free", "creator", "studio"]
DEFAULT_PLAN = "free"


def plan_details(plan_id: str) -> Dict[str, Any]:
    return PLANS.get(plan_id, PLANS[DEFAULT_PLAN])


def is_valid_plan(plan_id: str) -> bool:
    return plan_id in PLANS


def _month_start(now: Optional[datetime] = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def videos_used_this_month(db: AsyncSession, user: User) -> int:
    """Count render jobs for the user's projects since the 1st of this month."""
    project_ids = [
        row[0]
        for row in (await db.execute(select(Project.id).where(Project.user_id == user.id))).all()
    ]
    if not project_ids:
        return 0
    count = await db.scalar(
        select(func.count(RenderJob.id)).where(
            RenderJob.project_id.in_(project_ids),
            RenderJob.created_at >= _month_start(),
        )
    )
    return int(count or 0)


async def usage_summary(db: AsyncSession, user: User) -> Dict[str, Any]:
    plan_id = getattr(user, "plan", None) or DEFAULT_PLAN
    plan = plan_details(plan_id)
    used = await videos_used_this_month(db, user)
    limit = plan["videos_per_month"]
    remaining = UNLIMITED if limit == UNLIMITED else max(limit - used, 0)
    return {
        "plan": plan,
        "videos_used": used,
        "videos_limit": limit,
        "videos_remaining": remaining,
        "unlimited": limit == UNLIMITED,
        "period_start": _month_start().isoformat(),
    }


async def plan_allows_video(db: AsyncSession, user: User) -> bool:
    plan = plan_details(getattr(user, "plan", None) or DEFAULT_PLAN)
    if plan["videos_per_month"] == UNLIMITED:
        return True
    return (await videos_used_this_month(db, user)) < plan["videos_per_month"]


async def plan_allows_scheduling(user: User) -> bool:
    return bool(plan_details(getattr(user, "plan", None) or DEFAULT_PLAN)["scheduling"])


async def plan_watermark(user: User) -> bool:
    return bool(plan_details(getattr(user, "plan", None) or DEFAULT_PLAN)["watermark"])


# --- Stripe -----------------------------------------------------------------

STRIPE_API = "https://api.stripe.com/v1"


def stripe_configured() -> bool:
    return bool(settings.stripe_secret_key)


def _price_for(plan_id: str) -> str:
    # Only the Creator plan has a configurable price id today; Studio reuses it as a
    # placeholder until a second price is created in the dashboard.
    return settings.stripe_price_pro or ""


async def create_checkout_session(user: User, plan_id: str, success_url: str, cancel_url: str) -> Dict[str, Any]:
    """Return {"url": ...} for a Stripe Checkout redirect.

    Without a Stripe key this returns a local "demo" session URL so the upgrade flow can
    be exercised end-to-end; the caller then flips the plan directly.
    """
    if not stripe_configured():
        return {"mode": "demo", "url": f"{success_url}?demo_plan={plan_id}", "plan": plan_id}

    price_id = _price_for(plan_id)
    if not price_id:
        raise ValueError(
            "STRIPE_PRICE_PRO is not set. Create a recurring Price in the Stripe dashboard "
            "and put its id (price_...) in the environment."
        )

    data = {
        "mode": "subscription",
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": str(user.id),
        "customer_email": user.email,
        "metadata[plan]": plan_id,
        "metadata[user_id]": str(user.id),
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{STRIPE_API}/checkout/sessions",
            data=data,
            headers={"Authorization": f"Bearer {settings.stripe_secret_key}"},
        )
    if resp.status_code >= 400:
        logger.warning("Stripe checkout failed (%s): %s", resp.status_code, resp.text)
        raise ValueError("Stripe rejected the checkout request. Check the price id and secret key.")
    return {"mode": "stripe", "url": resp.json().get("url"), "plan": plan_id}


async def apply_plan(db: AsyncSession, user: User, plan_id: str, customer_id: Optional[str] = None) -> User:
    if not is_valid_plan(plan_id):
        raise ValueError(f"Unknown plan: {plan_id}")
    user.plan = plan_id
    if customer_id:
        user.stripe_customer_id = customer_id
    await db.flush()
    return user


def plan_catalog() -> List[Dict[str, Any]]:
    return [PLANS[p] for p in PLAN_ORDER]
