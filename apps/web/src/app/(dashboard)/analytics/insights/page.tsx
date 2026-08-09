'use client'

import { Bot, Lightbulb, TrendingUp, Zap, ArrowRight } from 'lucide-react'

const insights = [
  {
    type: 'performance',
    title: 'Your AI videos get 3x more views',
    description: 'Videos about AI topics consistently outperform other content. Consider creating more AI-focused content.',
    action: 'Get AI Video Ideas',
  },
  {
    type: 'timing',
    title: 'Best posting time: 10 AM & 6 PM',
    description: 'Your audience is most active during these times. Schedule your posts accordingly.',
    action: 'View Calendar',
  },
  {
    type: 'format',
    title: '30-second videos have highest retention',
    description: 'Your 30-second videos average 82% retention vs 68% for 60-second videos.',
    action: 'Adjust Default Duration',
  },
  {
    type: 'hook',
    title: 'Question hooks perform 40% better',
    description: 'Videos starting with a question ("Did you know...?") get significantly more views.',
    action: 'View Script Templates',
  },
]

export default function InsightsPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Bot className="w-6 h-6 text-violet-500" />
          AI Insights
        </h1>
        <p className="text-sm text-muted-foreground">AI-powered recommendations to improve your content</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Insights Generated</p>
          <p className="text-2xl font-bold">24</p>
          <p className="text-xs text-emerald-500 mt-1">+3 this week</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Implemented</p>
          <p className="text-2xl font-bold">18</p>
          <p className="text-xs text-emerald-500 mt-1">75% implementation rate</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Impact Score</p>
          <p className="text-2xl font-bold">+32%</p>
          <p className="text-xs text-emerald-500 mt-1">Performance improvement</p>
        </div>
      </div>

      <div className="space-y-4">
        {insights.map((insight, i) => (
          <div key={i} className="p-5 rounded-2xl bg-card border border-border hover:border-violet-500/30 transition-colors">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center shrink-0">
                {insight.type === 'performance' ? <TrendingUp className="w-5 h-5 text-violet-500" /> :
                 insight.type === 'timing' ? <Zap className="w-5 h-5 text-violet-500" /> :
                 <Lightbulb className="w-5 h-5 text-violet-500" />}
              </div>
              <div className="flex-1">
                <h3 className="font-semibold mb-1">{insight.title}</h3>
                <p className="text-sm text-muted-foreground mb-3">{insight.description}</p>
                <button className="flex items-center gap-1 text-sm text-violet-500 hover:underline font-medium">
                  {insight.action} <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
