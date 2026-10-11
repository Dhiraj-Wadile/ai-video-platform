'use client'

import { useEffect, useState } from 'react'
import { CreditCard, Check, Loader2, Sparkles, AlertCircle, Zap } from 'lucide-react'
import { api } from '@/lib/api'
import { useAppStore } from '@/lib/store'

interface Plan {
  id: string
  name: string
  price_cents: number
  videos_per_month: number
  max_resolution: string
  watermark: boolean
  scheduling: boolean
  api_access: boolean
  blurb?: string
}

interface Usage {
  plan: Plan
  videos_used: number
  videos_limit: number
  videos_remaining: number
  unlimited: boolean
}

export default function BillingPage() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [current, setCurrent] = useState('free')
  const [usage, setUsage] = useState<Usage | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const setUser = useAppStore((s) => s.setUser)
  const user = useAppStore((s) => s.user)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    setError('')
    try {
      const [planRes, usageRes]: any[] = await Promise.all([api.getPlans(), api.getUsage()])
      setPlans(planRes.plans || [])
      setCurrent(planRes.current_plan || 'free')
      setUsage(usageRes)
    } catch (err: any) {
      setError(err?.message || 'Could not load billing information.')
    } finally {
      setLoading(false)
    }
  }

  async function upgrade(planId: string) {
    setBusy(planId)
    setError('')
    setNotice('')
    try {
      const res: any = await api.billingCheckout(planId)
      if (res?.url && res.mode === 'stripe') {
        window.location.href = res.url
        return
      }
      // Demo mode: the plan was applied server-side immediately.
      setNotice(`You're now on the ${planId} plan. Enjoy!`)
      setCurrent(planId)
      const [usageRes, me]: any[] = await Promise.all([api.getUsage(), api.getMe()])
      setUsage(usageRes)
      setUser(me)
    } catch (err: any) {
      setError(err?.message || 'Upgrade failed. Please try again.')
    } finally {
      setBusy('')
    }
  }

  const priceLabel = (cents: number) => (cents === 0 ? 'Free' : `$${(cents / 100).toFixed(0)}/mo`)
  const planIndex = (id: string) => plans.findIndex((p) => p.id === id)

  const featureList = (p: Plan) => [
    p.videos_per_month === -1 ? 'Unlimited videos' : `${p.videos_per_month} videos / month`,
    `Up to ${p.max_resolution}`,
    p.watermark ? 'With watermark' : 'No watermark',
    p.scheduling ? 'Scheduling & queue' : 'Publish now only',
    p.api_access ? 'API access' : null,
  ].filter(Boolean) as string[]

  const pct = usage && !usage.unlimited && usage.videos_limit > 0
    ? Math.min(100, Math.round((usage.videos_used / usage.videos_limit) * 100))
    : 0

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <CreditCard className="w-6 h-6 text-violet-500" />
          Billing &amp; Plans
        </h1>
        <p className="text-sm text-muted-foreground">Manage your subscription and usage.</p>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-destructive/10 text-destructive text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}
      {notice && (
        <div className="p-4 rounded-2xl bg-emerald-500/10 text-emerald-500 text-sm flex items-center gap-2">
          <Check className="w-4 h-4 shrink-0" /> {notice}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
      ) : (
        <>
          <div className="p-4 sm:p-6 rounded-2xl bg-card border border-border">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
              <div>
                <p className="text-sm text-muted-foreground">Current plan</p>
                <p className="text-lg font-semibold capitalize flex items-center gap-2">
                  {current}
                  {user?.email && <span className="text-xs font-normal text-muted-foreground">({user.email})</span>}
                </p>
              </div>
              {usage && (
                <div className="text-right">
                  <p className="text-sm text-muted-foreground">This month</p>
                  <p className="text-lg font-semibold">
                    {usage.unlimited ? `${usage.videos_used} videos` : `${usage.videos_used} / ${usage.videos_limit}`}
                  </p>
                </div>
              )}
            </div>
            {usage && !usage.unlimited && (
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div
                  className={`h-full rounded-full ${pct >= 100 ? 'bg-red-500' : 'bg-gradient-to-r from-violet-500 to-purple-600'}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            )}
            {usage && usage.unlimited && (
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-violet-500" /> Unlimited videos on your plan.
              </p>
            )}
          </div>

          <div className="grid sm:grid-cols-3 gap-4">
            {plans.map((p) => {
              const isCurrent = p.id === current
              const isDowngrade = planIndex(p.id) < planIndex(current)
              return (
                <div
                  key={p.id}
                  className={`p-5 rounded-2xl bg-card border flex flex-col ${
                    isCurrent ? 'border-violet-500 ring-1 ring-violet-500' : 'border-border'
                  }`}
                >
                  {isCurrent && (
                    <span className="self-start text-[10px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-500 mb-2">Current</span>
                  )}
                  <h3 className="font-semibold text-lg">{p.name}</h3>
                  <p className="text-2xl font-bold mt-1">{priceLabel(p.price_cents)}</p>
                  {p.blurb && <p className="text-xs text-muted-foreground mt-1">{p.blurb}</p>}
                  <ul className="mt-4 space-y-2 flex-1">
                    {featureList(p).map((f) => (
                      <li key={f} className="flex items-center gap-2 text-sm">
                        <Check className="w-4 h-4 text-emerald-500 shrink-0" /> {f}
                      </li>
                    ))}
                  </ul>
                  <button
                    onClick={() => upgrade(p.id)}
                    disabled={isCurrent || isDowngrade || busy === p.id}
                    className={`mt-5 inline-flex items-center justify-center gap-2 py-2.5 rounded-xl font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
                      isCurrent
                        ? 'bg-muted text-muted-foreground'
                        : 'bg-gradient-to-r from-violet-600 to-purple-600 text-white hover:brightness-110'
                    }`}
                  >
                    {busy === p.id ? (
                      <><Loader2 className="w-4 h-4 animate-spin" /> Processing...</>
                    ) : isCurrent ? (
                      'Current plan'
                    ) : isDowngrade ? (
                      'Contact support'
                    ) : (
                      <><Zap className="w-4 h-4" /> Upgrade to {p.name}</>
                    )}
                  </button>
                </div>
              )
            })}
          </div>

          <p className="text-xs text-muted-foreground">
            Usage resets on the 1st of each month. Payments are handled securely by Stripe.
          </p>
        </>
      )}
    </div>
  )
}
