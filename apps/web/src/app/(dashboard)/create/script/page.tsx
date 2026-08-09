'use client'

import { useState, useEffect } from 'react'
import { Type, Sparkles, Loader2, Copy, RefreshCw } from 'lucide-react'
import { api } from '@/lib/api'

export default function ScriptPage() {
  const [topic, setTopic] = useState('')
  const [duration, setDuration] = useState('30s')
  const [style, setStyle] = useState('educational')
  const [generating, setGenerating] = useState(false)
  const [script, setScript] = useState<any>(null)
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    if (!topic.trim()) return
    setGenerating(true)
    setError('')
    try {
      const result: any = await api.generateScript({
        topic,
        duration,
        style,
      })
      setScript(result)
    } catch (err: any) {
      setError(err.message || 'Script generation failed')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Type className="w-6 h-6 text-violet-500" />
          Script Generator
        </h1>
        <p className="text-sm text-muted-foreground">AI-powered script generation with hook/setup/conflict/payoff/CTA structure</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-card border border-border space-y-4">
          <h2 className="font-semibold">Configure Script</h2>
          {error && (
            <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">{error}</div>
          )}
          <div>
            <label className="text-sm font-medium mb-2 block">Topic *</label>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., 5 money habits of successful people..."
              className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-violet-500 focus:ring-1 focus:ring-violet-500 outline-none text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Duration</label>
              <select value={duration} onChange={(e) => setDuration(e.target.value)} className="w-full px-4 py-3 rounded-xl bg-background border border-border text-sm">
                <option value="15s">15 seconds</option>
                <option value="30s">30 seconds</option>
                <option value="45s">45 seconds</option>
                <option value="60s">60 seconds</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Style</label>
              <select value={style} onChange={(e) => setStyle(e.target.value)} className="w-full px-4 py-3 rounded-xl bg-background border border-border text-sm">
                <option value="educational">Educational</option>
                <option value="comedy">Comedy</option>
                <option value="storytelling">Storytelling</option>
                <option value="motivational">Motivational</option>
              </select>
            </div>
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating || !topic.trim()}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-medium hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generating ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating...</> : <><Sparkles className="w-4 h-4" /> Generate Script</>}
          </button>
        </div>

        <div className="p-6 rounded-2xl bg-card border border-border space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Generated Script</h2>
            {script && (
              <button
                onClick={() => navigator.clipboard.writeText(script.content || script.full_script || JSON.stringify(script, null, 2))}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-muted text-sm hover:bg-accent transition-colors"
              >
                <Copy className="w-3 h-3" /> Copy
              </button>
            )}
          </div>
          {!script ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Type className="w-12 h-12 mb-3 opacity-50" />
              <p className="text-sm">Your AI-generated script will appear here</p>
              <p className="text-xs mt-1">Complete with hook, setup, conflict, payoff, and CTA</p>
            </div>
          ) : (
            <div className="space-y-4">
              {script.title && <h3 className="text-lg font-bold">{script.title}</h3>}
              {script.structure_json && typeof script.structure_json === 'object' && (
                <div className="space-y-3">
                  {['hook', 'setup', 'conflict', 'payoff', 'cta'].map((section) => {
                    const text = script.structure_json[section]
                    if (!text) return null
                    return (
                      <div key={section} className="p-3 rounded-xl bg-muted/50">
                        <p className="text-xs font-bold text-violet-500 uppercase mb-1">{section}</p>
                        <p className="text-sm">{typeof text === 'string' ? text : JSON.stringify(text)}</p>
                      </div>
                    )
                  })}
                </div>
              )}
              {script.full_script && (
                <div className="p-4 rounded-xl bg-background border border-border">
                  <p className="text-sm whitespace-pre-wrap">{script.full_script}</p>
                </div>
              )}
              {script.content && !script.full_script && (
                <div className="p-4 rounded-xl bg-background border border-border">
                  <p className="text-sm whitespace-pre-wrap">{script.content}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
