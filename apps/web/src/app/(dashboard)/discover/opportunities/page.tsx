'use client'

import { useState } from 'react'
import { BarChart3, TrendingUp, Target, Zap, ArrowRight, RefreshCw } from 'lucide-react'

const opportunities = [
  {
    id: '1',
    topic: 'AI Agents Explained',
    opportunity: 'High search volume, low competition in short-form',
    score: 92,
    searchVolume: 'High',
    competition: 'Low',
    format: 'Educational',
    suggestedDuration: '30s',
  },
  {
    id: '2',
    topic: 'Side Hustle Ideas 2026',
    opportunity: 'Trending topic with viral potential',
    score: 87,
    searchVolume: 'Very High',
    competition: 'Medium',
    format: 'Listicle',
    suggestedDuration: '45s',
  },
  {
    id: '3',
    topic: 'Money Mistakes Young People Make',
    opportunity: 'Evergreen topic with high engagement',
    score: 84,
    searchVolume: 'High',
    competition: 'Medium',
    format: 'Storytelling',
    suggestedDuration: '60s',
  },
]

export default function OpportunitiesPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-violet-500" />
            Content Opportunities
          </h1>
          <p className="text-sm text-muted-foreground">AI-identified high-potential content topics</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500/10 text-violet-500 font-medium hover:bg-violet-500/20 transition-colors text-sm">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Opportunities Found</p>
          <p className="text-2xl font-bold">12</p>
          <p className="text-xs text-emerald-500 mt-1">+3 new today</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Avg Score</p>
          <p className="text-2xl font-bold">87</p>
          <p className="text-xs text-emerald-500 mt-1">Above average</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Quick Win Topics</p>
          <p className="text-2xl font-bold">5</p>
          <p className="text-xs text-violet-500 mt-1">High score, low competition</p>
        </div>
      </div>

      <div className="space-y-3">
        {opportunities.map((opp) => (
          <div key={opp.id} className="p-5 rounded-2xl bg-card border border-border hover:border-violet-500/30 transition-colors">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="font-semibold">{opp.topic}</h3>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-500 font-bold">
                    {opp.score}/100
                  </span>
                </div>
                <p className="text-sm text-muted-foreground mb-3">{opp.opportunity}</p>
                <div className="flex items-center gap-4 text-xs">
                  <span className="flex items-center gap-1 text-muted-foreground">
                    <TrendingUp className="w-3 h-3" /> Volume: {opp.searchVolume}
                  </span>
                  <span className="flex items-center gap-1 text-muted-foreground">
                    <Target className="w-3 h-3" /> Competition: {opp.competition}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-muted">{opp.format}</span>
                  <span className="text-muted-foreground">{opp.suggestedDuration}</span>
                </div>
              </div>
              <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-violet-500/10 text-violet-500 text-xs font-medium hover:bg-violet-500/20 transition-colors shrink-0">
                Create <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
