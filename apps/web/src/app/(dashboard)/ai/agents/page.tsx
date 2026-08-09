'use client'

import { useState, useEffect } from 'react'
import { Bot, Activity, Clock, CheckCircle2, XCircle, Loader2, Play } from 'lucide-react'
import { api } from '@/lib/api'

export default function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [runningAgent, setRunningAgent] = useState<string | null>(null)
  const [runInput, setRunInput] = useState('')
  const [runResult, setRunResult] = useState<any>(null)

  useEffect(() => { loadAgents() }, [])

  async function loadAgents() {
    try {
      const data: any = await api.getAgents()
      const list = data.agents || data || []
      setAgents(Array.isArray(list) ? list : [])
    } catch {
      // Default agents on error
      setAgents([
        { name: 'trend', description: 'Analyzes trending topics for content potential' },
        { name: 'script', description: 'Generates retention-optimized video scripts' },
        { name: 'storyboard', description: 'Converts scripts to scene-by-scene breakdowns' },
        { name: 'character', description: 'Creates original fictional characters' },
        { name: 'quality', description: 'Reviews content quality across multiple dimensions' },
      ])
    } finally {
      setLoading(false)
    }
  }

  async function handleRunAgent(agentName: string) {
    if (!runInput.trim()) return
    setRunningAgent(agentName)
    setRunResult(null)
    try {
      const result: any = await api.runAgent(agentName, { content: runInput })
      setRunResult({ agent: agentName, ...result })
    } catch (err: any) {
      setRunResult({ agent: agentName, error: err.message })
    } finally {
      setRunningAgent(null)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Bot className="w-6 h-6 text-violet-500" />
          AI Agents
        </h1>
        <p className="text-sm text-muted-foreground">Monitor and run your AI agents</p>
      </div>

      <div className="p-5 rounded-2xl bg-card border border-border space-y-4">
        <h2 className="font-semibold">Quick Agent Run</h2>
        <div className="flex items-center gap-3">
          <input
            value={runInput}
            onChange={(e) => setRunInput(e.target.value)}
            placeholder="Enter content for the agent to process..."
            className="flex-1 px-4 py-2 rounded-xl bg-background border border-border text-sm focus:border-violet-500 outline-none"
            onKeyDown={(e) => e.key === 'Enter' && agents[0] && handleRunAgent(agents[0].name)}
          />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
      ) : (
        <div className="space-y-3">
          {agents.map((agent: any) => {
            const name = agent.name || agent
            const description = agent.description || 'AI Agent'
            return (
              <div key={name} className="p-5 rounded-2xl bg-card border border-border hover:border-violet-500/30 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-violet-500/10 flex items-center justify-center">
                      <Bot className="w-6 h-6 text-violet-500" />
                    </div>
                    <div>
                      <h3 className="font-semibold capitalize">{name} Agent</h3>
                      <p className="text-sm text-muted-foreground">{description}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleRunAgent(name)}
                    disabled={!runInput.trim() || runningAgent === name}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-violet-500/10 text-violet-500 text-xs font-medium hover:bg-violet-500/20 transition-colors disabled:opacity-50"
                  >
                    {runningAgent === name ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                    Run
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {runResult && (
        <div className="p-5 rounded-2xl bg-card border border-border">
          <h2 className="font-semibold mb-3">Agent Result: {runResult.agent}</h2>
          {runResult.error ? (
            <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">{runResult.error}</div>
          ) : (
            <div className="space-y-3">
              {runResult.content && (
                <div className="p-4 rounded-xl bg-background border border-border">
                  <p className="text-sm whitespace-pre-wrap">{runResult.content}</p>
                </div>
              )}
              {runResult.structured_data && (
                <pre className="p-4 rounded-xl bg-background border border-border text-xs overflow-auto max-h-64">
                  {JSON.stringify(runResult.structured_data, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
