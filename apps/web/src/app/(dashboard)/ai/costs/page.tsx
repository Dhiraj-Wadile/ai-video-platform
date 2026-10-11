'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { DollarSign, Loader2, AlertCircle, TrendingDown } from 'lucide-react'
import { api } from '@/lib/api'
import { formatCost, formatCostPrecise, formatMs } from '@/lib/utils'

interface CostTotals {
  cost_cents: number
  latency_ms: number
  calls: number
}

interface ProjectCost {
  project_id: string
  cost_cents: number
  latency_ms: number
  calls: number
}

export default function CostsPage() {
  const [totals, setTotals] = useState<CostTotals | null>(null)
  const [perProject, setPerProject] = useState<ProjectCost[]>([])
  const [names, setNames] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => { loadCosts() }, [])

  async function loadCosts() {
    try {
      const data: any = await api.getCosts()
      setTotals(data.totals || null)
      setPerProject(Array.isArray(data.per_project) ? data.per_project : [])
      const projects: any = await api.getProjects()
      const list = projects.projects || projects || []
      const map: Record<string, string> = {}
      ;(Array.isArray(list) ? list : []).forEach((p: any) => { map[p.id] = p.name || 'Untitled' })
      setNames(map)
    } catch (err: any) {
      setError(err.message || 'Could not load cost data')
    } finally {
      setLoading(false)
    }
  }

  const maxCost = Math.max(...perProject.map((p) => p.cost_cents), 1)
  const costPerCall = totals && totals.calls > 0 ? totals.cost_cents / totals.calls : 0

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <DollarSign className="w-6 h-6 text-violet-500" />
          Cost Management
        </h1>
        <p className="text-sm text-muted-foreground">Where your AI generation budget actually goes</p>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-destructive/10 text-destructive text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[
              { label: 'Total Spend', value: formatCost(totals?.cost_cents) },
              { label: 'Provider Calls', value: String(totals?.calls ?? 0) },
              { label: 'Cost per Call', value: formatCostPrecise(costPerCall) },
              { label: 'Total Latency', value: formatMs(totals?.latency_ms) },
            ].map((stat) => (
              <div key={stat.label} className="p-4 rounded-2xl bg-card border border-border">
                <p className="text-sm text-muted-foreground mb-1">{stat.label}</p>
                <p className="text-2xl font-bold">{stat.value}</p>
              </div>
            ))}
          </div>

          <div className="p-4 rounded-2xl bg-card border border-border">
            <h2 className="font-semibold text-sm mb-4">Spend by project</h2>
            {perProject.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No recorded generation cost yet. Costs appear once a project runs the AI pipeline.{' '}
                <Link href="/create/new" className="text-violet-500 hover:underline">Generate a video</Link>
              </p>
            ) : (
              <div className="space-y-3">
                {perProject.map((item) => (
                  <div key={item.project_id} className="flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <Link
                          href={`/studio/editor?project=${item.project_id}`}
                          className="text-xs font-medium truncate hover:text-violet-500"
                        >
                          {names[item.project_id] || 'Untitled project'}
                        </Link>
                        <p className="text-xs text-muted-foreground shrink-0 ml-3">
                          {formatCost(item.cost_cents)} &middot; {item.calls} calls
                        </p>
                      </div>
                      <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full bg-violet-500 rounded-full"
                          style={{ width: `${(item.cost_cents / maxCost) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {perProject.length > 1 && (
            <div className="p-4 rounded-2xl bg-card border border-border flex items-center gap-3">
              <TrendingDown className="w-5 h-5 text-emerald-500" />
              <p className="text-sm text-muted-foreground">
                Regenerating a single scene costs only that scene&apos;s image call. Reuse a good scene
                instead of re-rendering the whole video.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
