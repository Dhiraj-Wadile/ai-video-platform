'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Activity, Clock, CheckCircle2, XCircle, Loader2, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { formatCostPrecise, formatDate, formatMs } from '@/lib/utils'

interface Run {
  id: string
  project_id: string
  agent: string
  status: string
  model: string | null
  cost_cents: number | null
  tokens_in: number | null
  tokens_out: number | null
  latency_ms: number | null
  error: string | null
  created_at: string | null
}

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => { loadRuns() }, [])

  async function loadRuns() {
    try {
      const data: any = await api.getAgentRuns()
      setRuns(Array.isArray(data.runs) ? data.runs : [])
    } catch (err: any) {
      setError(err.message || 'Could not load agent runs')
    } finally {
      setLoading(false)
    }
  }

  const completed = runs.filter((r) => r.status === 'completed').length
  const successRate = runs.length > 0 ? Math.round((completed / runs.length) * 100) : 0
  const totalCost = runs.reduce((sum, r) => sum + (r.cost_cents || 0), 0)
  const avgLatency = runs.length > 0
    ? Math.round(runs.reduce((sum, r) => sum + (r.latency_ms || 0), 0) / runs.length)
    : 0

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Activity className="w-6 h-6 text-violet-500" />
          Agent Runs
        </h1>
        <p className="text-sm text-muted-foreground">Every AI agent execution across your projects</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Runs', value: String(runs.length) },
          { label: 'Success Rate', value: runs.length ? `${successRate}%` : '—' },
          { label: 'Avg Latency', value: formatMs(avgLatency) },
          { label: 'Total Cost', value: formatCostPrecise(totalCost) },
        ].map((stat) => (
          <div key={stat.label} className="p-4 rounded-2xl bg-card border border-border">
            <p className="text-sm text-muted-foreground mb-1">{stat.label}</p>
            <p className="text-2xl font-bold">{stat.value}</p>
          </div>
        ))}
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
      ) : runs.length === 0 ? (
        <div className="p-12 rounded-2xl bg-card border border-border text-center">
          <Activity className="w-10 h-10 mx-auto text-muted-foreground mb-3 opacity-50" />
          <p className="text-muted-foreground mb-3">No agent runs yet</p>
          <Link href="/create/new" className="text-violet-500 text-sm hover:underline">Generate a video</Link>
        </div>
      ) : (
        <div className="space-y-2">
          {runs.map((run) => (
            <div key={run.id} className="p-4 rounded-2xl bg-card border border-border flex items-center gap-4">
              {run.status === 'completed'
                ? <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                : <XCircle className="w-5 h-5 text-red-500 shrink-0" />}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{run.agent}</p>
                <p className="text-xs text-muted-foreground">
                  {run.created_at ? formatDate(run.created_at) : 'unknown time'}
                </p>
                {run.error && <p className="text-xs text-red-500 mt-1 break-words">{run.error}</p>}
              </div>
              <div className="flex items-center gap-4 text-xs text-muted-foreground shrink-0">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" /> {formatMs(run.latency_ms)}
                </span>
                <span className="hidden sm:inline">{run.model || '—'}</span>
                <span>{((run.tokens_in || 0) + (run.tokens_out || 0)).toLocaleString()} tokens</span>
                <span>{formatCostPrecise(run.cost_cents)}</span>
              </div>

            </div>
          ))}
        </div>
      )}
    </div>
  )
}
