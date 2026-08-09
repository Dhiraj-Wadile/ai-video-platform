'use client'

import { DollarSign, TrendingDown, TrendingUp, BarChart3 } from 'lucide-react'

const costBreakdown = [
  { category: 'LLM (Script Generation)', cost: 4.20, percentage: 50, trend: '-12%' },
  { category: 'LLM (Storyboard)', cost: 2.10, percentage: 25, trend: '-8%' },
  { category: 'LLM (Quality Check)', cost: 0.84, percentage: 10, trend: '+5%' },
  { category: 'Voice (TTS)', cost: 0.92, percentage: 11, trend: '+2%' },
  { category: 'Image Generation', cost: 0.00, percentage: 0, trend: 'Free' },
  { category: 'Storage', cost: 0.36, percentage: 4, trend: '+15%' },
]

const dailyCosts = [
  { date: 'Mon', cost: 1.20 },
  { date: 'Tue', cost: 0.85 },
  { date: 'Wed', cost: 2.10 },
  { date: 'Thu', cost: 1.50 },
  { date: 'Fri', cost: 1.80 },
  { date: 'Sat', cost: 0.60 },
  { date: 'Sun', cost: 0.37 },
]

export default function CostsPage() {
  const totalCost = costBreakdown.reduce((sum, c) => sum + c.cost, 0)
  const maxDaily = Math.max(...dailyCosts.map(d => d.cost))

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <DollarSign className="w-6 h-6 text-violet-500" />
          Cost Management
        </h1>
        <p className="text-sm text-muted-foreground">Track AI generation costs and optimize spending</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">This Month</p>
          <p className="text-2xl font-bold">${totalCost.toFixed(2)}</p>
          <p className="text-xs text-emerald-500 mt-1 flex items-center gap-1"><TrendingDown className="w-3 h-3" /> -15% vs last month</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Budget Used</p>
          <p className="text-2xl font-bold">16.8%</p>
          <div className="w-full h-1.5 rounded-full bg-muted mt-2 overflow-hidden">
            <div className="h-full bg-violet-500 rounded-full" style={{ width: '16.8%' }} />
          </div>
          <p className="text-xs text-muted-foreground mt-1">$8.42 of $50.00</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Cost per Video</p>
          <p className="text-2xl font-bold">$0.35</p>
          <p className="text-xs text-emerald-500 mt-1 flex items-center gap-1"><TrendingDown className="w-3 h-3" /> -8% vs last week</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Projected Monthly</p>
          <p className="text-2xl font-bold">$12.60</p>
          <p className="text-xs text-emerald-500 mt-1">Under budget</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-4 rounded-2xl bg-card border border-border">
          <h2 className="font-semibold text-sm mb-4">Daily Costs (This Week)</h2>
          <div className="flex items-end gap-2 h-40">
            {dailyCosts.map((day) => (
              <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-[10px] text-muted-foreground">${day.cost.toFixed(2)}</span>
                <div
                  className="w-full bg-gradient-to-t from-violet-500 to-purple-500 rounded-t transition-all"
                  style={{ height: `${(day.cost / maxDaily) * 100}%`, minHeight: '4px' }}
                />
                <span className="text-[10px] text-muted-foreground">{day.date}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-card border border-border">
          <h2 className="font-semibold text-sm mb-4">Cost Breakdown</h2>
          <div className="space-y-3">
            {costBreakdown.map((item) => (
              <div key={item.category} className="flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs font-medium truncate">{item.category}</p>
                    <p className="text-xs text-muted-foreground">${item.cost.toFixed(2)}</p>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden">
                    <div className="h-full bg-violet-500 rounded-full" style={{ width: `${item.percentage}%` }} />
                  </div>
                </div>
                <span className="text-[10px] text-muted-foreground w-12 text-right">{item.trend}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="p-4 rounded-2xl bg-card border border-border">
        <h2 className="font-semibold text-sm mb-3">Quality Mode</h2>
        <div className="grid grid-cols-3 gap-3">
          {[
            { name: 'Cheap', desc: 'Fastest, lowest cost', cost: '~$0.15/video' },
            { name: 'Balanced', desc: 'Good quality, moderate cost', cost: '~$0.35/video', recommended: true },
            { name: 'High Quality', desc: 'Best quality, higher cost', cost: '~$0.80/video' },
          ].map((mode) => (
            <div key={mode.name} className={`p-4 rounded-xl border text-center transition-colors cursor-pointer ${
              mode.recommended ? 'border-violet-500/50 bg-violet-500/5' : 'border-border hover:border-violet-500/20'
            }`}>
              {mode.recommended && <span className="text-[10px] text-violet-500 font-medium">Recommended</span>}
              <p className="font-semibold mt-1">{mode.name}</p>
              <p className="text-xs text-muted-foreground mt-1">{mode.desc}</p>
              <p className="text-xs text-muted-foreground mt-2">{mode.cost}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
