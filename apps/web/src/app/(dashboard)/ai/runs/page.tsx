'use client'

import { useState } from 'react'
import { Activity, Clock, CheckCircle2, XCircle, ChevronDown, ChevronUp } from 'lucide-react'

const runs = [
  { id: '1', agent: 'Script Agent', status: 'completed', input: 'AI habits for entrepreneurs', output: 'Generated 30s script...', latency: '3.2s', tokens: '1,240', cost: '$0.02', time: '2 hours ago' },
  { id: '2', agent: 'Storyboard Agent', status: 'completed', input: 'Script content...', output: '5 scenes planned', latency: '4.8s', tokens: '2,100', cost: '$0.04', time: '2 hours ago' },
  { id: '3', agent: 'Quality Agent', status: 'completed', input: 'Full video content...', output: 'Score: 87/100', latency: '2.1s', tokens: '980', cost: '$0.01', time: '2 hours ago' },
  { id: '4', agent: 'Trend Agent', status: 'failed', input: 'Current trends', output: 'API timeout', latency: '5.0s', tokens: '0', cost: '$0.00', time: '3 hours ago' },
  { id: '5', agent: 'Script Agent', status: 'completed', input: 'Money tips', output: 'Generated 45s script...', latency: '3.8s', tokens: '1,580', cost: '$0.03', time: '5 hours ago' },
]

export default function RunsPage() {
  const [expandedRun, setExpandedRun] = useState<string | null>(null)

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Activity className="w-6 h-6 text-violet-500" />
          Agent Runs
        </h1>
        <p className="text-sm text-muted-foreground">Monitor all AI agent executions</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Total Runs</p>
          <p className="text-2xl font-bold">170</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Success Rate</p>
          <p className="text-2xl font-bold text-emerald-500">96%</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Avg Latency</p>
          <p className="text-2xl font-bold">3.4s</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Total Cost</p>
          <p className="text-2xl font-bold">$8.42</p>
        </div>
      </div>

      <div className="space-y-2">
        {runs.map((run) => (
          <div key={run.id} className="rounded-2xl bg-card border border-border overflow-hidden">
            <div
              className="p-4 flex items-center justify-between cursor-pointer hover:bg-muted/50 transition-colors"
              onClick={() => setExpandedRun(expandedRun === run.id ? null : run.id)}
            >
              <div className="flex items-center gap-3">
                {run.status === 'completed' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-500" />
                )}
                <div>
                  <p className="text-sm font-medium">{run.agent}</p>
                  <p className="text-xs text-muted-foreground">{run.time}</p>
                </div>
              </div>
              <div className="flex items-center gap-6 text-xs text-muted-foreground">
                <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {run.latency}</span>
                <span>{run.tokens} tokens</span>
                <span>{run.cost}</span>
                {expandedRun === run.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </div>
            </div>
            {expandedRun === run.id && (
              <div className="px-4 pb-4 border-t border-border pt-3 space-y-2">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Input</p>
                  <p className="text-sm bg-muted/50 rounded-lg p-2 font-mono">{run.input}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Output</p>
                  <p className="text-sm bg-muted/50 rounded-lg p-2 font-mono">{run.output}</p>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
