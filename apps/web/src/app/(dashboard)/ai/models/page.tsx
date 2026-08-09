'use client'

import { Cpu, CheckCircle2, XCircle } from 'lucide-react'

const models = [
  { provider: 'OpenAI', model: 'GPT-4o', status: 'active', latency: '2.1s', cost: '$2.50/1M input', quality: 'Excellent' },
  { provider: 'OpenAI', model: 'GPT-4o Mini', status: 'active', latency: '0.8s', cost: '$0.15/1M input', quality: 'Good' },
  { provider: 'Anthropic', model: 'Claude Sonnet', status: 'active', latency: '2.5s', cost: '$3.00/1M input', quality: 'Excellent' },
  { provider: 'ElevenLabs', model: 'Multilingual v2', status: 'active', latency: '1.2s', cost: '$0.30/1K chars', quality: 'Excellent' },
  { provider: 'Edge TTS', model: 'Neural Voices', status: 'active', latency: '0.5s', cost: 'Free', quality: 'Good' },
  { provider: 'Pollinations', model: 'Image Gen', status: 'active', latency: '3.0s', cost: 'Free', quality: 'Standard' },
]

export default function ModelsPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Cpu className="w-6 h-6 text-violet-500" />
          AI Models
        </h1>
        <p className="text-sm text-muted-foreground">Configure AI provider models and settings</p>
      </div>

      <div className="space-y-3">
        {models.map((model, i) => (
          <div key={i} className="p-5 rounded-2xl bg-card border border-border hover:border-violet-500/30 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-violet-500/10 flex items-center justify-center">
                  <Cpu className="w-6 h-6 text-violet-500" />
                </div>
                <div>
                  <h3 className="font-semibold">{model.model}</h3>
                  <p className="text-sm text-muted-foreground">{model.provider}</p>
                </div>
              </div>
              <div className="flex items-center gap-6">
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Latency</p>
                  <p className="text-sm font-medium">{model.latency}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Cost</p>
                  <p className="text-sm font-medium">{model.cost}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Quality</p>
                  <p className="text-sm font-medium">{model.quality}</p>
                </div>
                <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                  model.status === 'active' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'
                }`}>
                  {model.status === 'active' ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                  {model.status}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
