'use client'

import { useEffect, useState } from 'react'
import { Settings, Cpu, CheckCircle2, XCircle, Loader2, AlertCircle, User, ShieldCheck } from 'lucide-react'
import { api } from '@/lib/api'
import { useAppStore } from '@/lib/store'

interface ProviderInfo {
  name: string
  task: string
  vendor: string
  models: string[]
  configured: boolean
  enabled: boolean
  is_mock: boolean
  priority: number
}

export default function SettingsPage() {
  const { user } = useAppStore()
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const data: any = await api.getProviders()
      setProviders(Array.isArray(data.providers) ? data.providers : [])
    } catch (err: any) {
      setError(err.message || 'Could not load provider status')
    } finally {
      setLoading(false)
    }
  }

  const byTask = providers.reduce((acc: Record<string, ProviderInfo[]>, p) => {
    (acc[p.task] = acc[p.task] || []).push(p)
    return acc
  }, {})
  const live = providers.filter((p) => p.configured && !p.is_mock).length

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="w-6 h-6 text-violet-500" />
          Settings
        </h1>
        <p className="text-sm text-muted-foreground">Your account and the providers powering generation</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="p-4 rounded-2xl bg-card border border-border space-y-3 h-fit">
          <h2 className="font-semibold text-sm flex items-center gap-2">
            <User className="w-4 h-4" /> Account
          </h2>
          <div className="text-sm space-y-1">
            <p className="font-medium">{user?.name || 'Signed in'}</p>
            <p className="text-muted-foreground break-all">{user?.email}</p>
          </div>
          <div className="flex items-start gap-2 pt-3 border-t border-border">
            <ShieldCheck className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
            <p className="text-xs text-muted-foreground">
              Provider credentials live on the server only. They are never sent to this browser.
            </p>
          </div>
        </div>

        <div className="lg:col-span-2 p-4 rounded-2xl bg-card border border-border space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-sm flex items-center gap-2">
              <Cpu className="w-4 h-4" /> AI Providers
            </h2>
            <span className="text-xs text-muted-foreground">
              {live} live &middot; {providers.length} registered
            </span>
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-destructive/10 text-destructive text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" /> {error}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : providers.length === 0 ? (
            <p className="text-sm text-muted-foreground">No providers registered.</p>
          ) : (
            <div className="space-y-4">
              {Object.entries(byTask).map(([task, list]) => (
                <div key={task}>
                  <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">{task}</p>
                  <div className="space-y-2">
                    {list.map((p) => (
                      <div key={p.name} className="p-3 rounded-xl bg-muted/40 flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-sm font-medium">
                            {p.name}
                            {p.is_mock && (
                              <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-500">
                                mock
                              </span>
                            )}
                          </p>
                          <p className="text-xs text-muted-foreground truncate">
                            {p.vendor}
                            {p.models.length > 0 ? ` · ${p.models.join(', ')}` : ''}
                          </p>
                        </div>
                        {p.configured ? (
                          <span className="flex items-center gap-1 text-xs text-emerald-500 shrink-0">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Ready
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
                            <XCircle className="w-3.5 h-3.5" /> No key set
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          <p className="text-xs text-muted-foreground pt-3 border-t border-border">
            Providers are selected automatically by capability and priority. A provider without a server-side
            key is skipped, and mock providers are only used as a last resort.
          </p>
        </div>
      </div>
    </div>
  )
}
