'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, ArrowUpRight, Search, Sparkles, Loader2, RefreshCw } from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'

export default function TrendsPage() {
  const [trends, setTrends] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [analyzeTopic, setAnalyzeTopic] = useState('')

  useEffect(() => { loadTrends() }, [])

  async function loadTrends() {
    try {
      const data: any = await api.getTrends()
      const list = data.trends || data || []
      setTrends(Array.isArray(list) ? list : [])
    } catch {
      // Use fallback data
    } finally {
      setLoading(false)
    }
  }

  async function handleAnalyze() {
    if (!analyzeTopic.trim()) return
    setAnalyzing(true)
    try {
      const result: any = await api.analyzeTrend(analyzeTopic)
      if (result) {
        setTrends((prev) => [{ ...result, topic: analyzeTopic }, ...prev])
      }
      setAnalyzeTopic('')
    } catch {
      // Handle error silently
    } finally {
      setAnalyzing(false)
    }
  }

  const filtered = trends.filter((t) =>
    !searchQuery || (t.topic || '').toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-violet-500" />
            Trending Topics
          </h1>
          <p className="text-sm text-muted-foreground">Discover trending topics and content opportunities</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search trends..."
              className="pl-9 pr-4 py-2 rounded-lg bg-background border border-border text-sm focus:border-violet-500 focus:ring-1 focus:ring-violet-500 outline-none"
            />
          </div>
          <button onClick={loadTrends} className="p-2 rounded-lg bg-muted hover:bg-accent transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="p-4 rounded-2xl bg-card border border-border">
        <div className="flex items-center gap-3">
          <input
            value={analyzeTopic}
            onChange={(e) => setAnalyzeTopic(e.target.value)}
            placeholder="Analyze a topic for viral potential..."
            className="flex-1 px-4 py-2 rounded-xl bg-background border border-border text-sm focus:border-violet-500 outline-none"
            onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
          />
          <button
            onClick={handleAnalyze}
            disabled={analyzing || !analyzeTopic.trim()}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500 text-white text-sm font-medium hover:bg-violet-600 transition-colors disabled:opacity-50"
          >
            {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            Analyze
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Active Trends</p>
          <p className="text-2xl font-bold">{trends.length}</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">High Score (80+)</p>
          <p className="text-2xl font-bold">{trends.filter((t) => (t.score || 0) >= 80).length}</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Avg Score</p>
          <p className="text-2xl font-bold">{trends.length ? Math.round(trends.reduce((a, t) => a + (t.score || 0), 0) / trends.length) : 0}</p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12">
          <TrendingUp className="w-12 h-12 mx-auto text-muted-foreground mb-3 opacity-50" />
          <p className="text-muted-foreground">No trends found. Try analyzing a topic above!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((trend: any, i: number) => (
            <div key={trend.id || i} className="p-5 rounded-2xl bg-card border border-border hover:border-violet-500/30 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold">{trend.topic}</h3>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-500 font-medium">
                      {trend.score || '—'}/100
                    </span>
                  </div>
                  {trend.metadata_json && typeof trend.metadata_json === 'object' && (
                    <div className="flex items-center gap-4 text-xs text-muted-foreground mt-2">
                      {trend.metadata_json.format && <span>Format: {trend.metadata_json.format}</span>}
                      {trend.metadata_json.duration && <span>Duration: {trend.metadata_json.duration}</span>}
                      {trend.metadata_json.audience && <span>Audience: {trend.metadata_json.audience}</span>}
                    </div>
                  )}
                </div>
                <Link
                  href={`/create/new?topic=${encodeURIComponent(trend.topic)}`}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-violet-500/10 text-violet-500 text-xs font-medium hover:bg-violet-500/20 transition-colors"
                >
                  <Sparkles className="w-3 h-3" /> Create
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
