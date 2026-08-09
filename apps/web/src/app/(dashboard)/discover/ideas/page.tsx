'use client'

import { useState } from 'react'
import { Sparkles, Lightbulb, RefreshCw, ThumbsUp, ThumbsDown, Target, Zap, Star } from 'lucide-react'

const ideas = [
  {
    id: '1',
    title: 'Why 99% of People Fail at Investing',
    hook: 'The #1 reason you\'re still broke...',
    format: 'Educational',
    duration: '30s',
    hookStrength: 92,
    entertainment: 75,
    novelty: 68,
    audienceRelevance: 88,
    retentionPotential: 85,
    overallScore: 82,
  },
  {
    id: '2',
    title: 'The AI Secret Nobody Tells You',
    hook: 'AI is about to change everything...',
    format: 'Storytelling',
    duration: '45s',
    hookStrength: 88,
    entertainment: 82,
    novelty: 90,
    audienceRelevance: 85,
    retentionPotential: 80,
    overallScore: 85,
  },
  {
    id: '3',
    title: '3 Habits That Changed My Life',
    hook: 'Do this every morning...',
    format: 'Motivational',
    duration: '30s',
    hookStrength: 85,
    entertainment: 70,
    novelty: 60,
    audienceRelevance: 92,
    retentionPotential: 88,
    overallScore: 79,
  },
]

export default function IdeasPage() {
  const [selectedIdea, setSelectedIdea] = useState<string | null>(null)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Lightbulb className="w-6 h-6 text-violet-500" />
            Content Ideas
          </h1>
          <p className="text-sm text-muted-foreground">AI-generated video ideas with scoring</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500/10 text-violet-500 font-medium hover:bg-violet-500/20 transition-colors text-sm">
          <RefreshCw className="w-4 h-4" /> Generate More
        </button>
      </div>

      <div className="space-y-4">
        {ideas.map((idea) => (
          <div
            key={idea.id}
            className={`p-5 rounded-2xl bg-card border transition-all cursor-pointer ${
              selectedIdea === idea.id ? 'border-violet-500/50 ring-1 ring-violet-500/20' : 'border-border hover:border-violet-500/30'
            }`}
            onClick={() => setSelectedIdea(selectedIdea === idea.id ? null : idea.id)}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="font-semibold">{idea.title}</h3>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-500 font-bold">
                    {idea.overallScore}/100
                  </span>
                </div>
                <p className="text-sm text-muted-foreground italic mb-3">&ldquo;{idea.hook}&rdquo;</p>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="px-2 py-0.5 rounded-full bg-muted">{idea.format}</span>
                  <span>{idea.duration}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button className="p-1.5 rounded-lg hover:bg-emerald-500/10 transition-colors">
                  <ThumbsUp className="w-4 h-4 text-muted-foreground hover:text-emerald-500" />
                </button>
                <button className="p-1.5 rounded-lg hover:bg-red-500/10 transition-colors">
                  <ThumbsDown className="w-4 h-4 text-muted-foreground hover:text-red-500" />
                </button>
              </div>
            </div>

            {selectedIdea === idea.id && (
              <div className="mt-4 pt-4 border-t border-border space-y-3">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {[
                    { label: 'Hook Strength', value: idea.hookStrength, icon: Zap },
                    { label: 'Entertainment', value: idea.entertainment, icon: Star },
                    { label: 'Novelty', value: idea.novelty, icon: Lightbulb },
                    { label: 'Audience', value: idea.audienceRelevance, icon: Target },
                    { label: 'Retention', value: idea.retentionPotential, icon: Target },
                  ].map((metric) => (
                    <div key={metric.label} className="p-3 rounded-xl bg-muted/50 text-center">
                      <metric.icon className="w-4 h-4 mx-auto text-violet-500 mb-1" />
                      <p className="text-lg font-bold">{metric.value}</p>
                      <p className="text-[10px] text-muted-foreground">{metric.label}</p>
                    </div>
                  ))}
                </div>
                <button className="w-full py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white text-sm font-medium hover:brightness-110 transition-all">
                  Create Video from This Idea
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
