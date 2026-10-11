'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  Video, TrendingUp, Sparkles, DollarSign, BarChart3, Wand2, Loader2, AlertCircle,
  Lightbulb, MousePointerClick, Rocket, RefreshCw,
} from 'lucide-react'
import { api } from '@/lib/api'
import { VIDEO_IDEAS, ONBOARDING_KEY } from '@/lib/utils'

interface Project {
  id: string
  name?: string
  title?: string
  status?: string
  platform?: string
  project_type?: string
}

interface Trend {
  id?: string
  topic?: string
  score?: number
  source?: string
}

const onboardingSteps = [
  { icon: Lightbulb, title: 'Pick an idea', desc: 'Type a topic or use a ready-made one.' },
  { icon: Wand2, title: 'AI builds it', desc: 'Script, scenes, voice and render are automatic.' },
  { icon: Rocket, title: 'Review & publish', desc: 'Tweak anything, then post to your platforms.' },
]

export default function DashboardPage() {
  const [stats, setStats] = useState([
    { label: 'Videos Created', value: '0', change: 'Total projects', icon: Video, color: 'text-violet-500' },
    { label: 'Videos Published', value: '0', change: 'Published', icon: TrendingUp, color: 'text-emerald-500' },
    { label: 'Generation Cost', value: '$0.00', change: 'All time', icon: DollarSign, color: 'text-amber-500' },
    { label: 'Total Views', value: '0', change: 'Across platforms', icon: BarChart3, color: 'text-blue-500' },
  ])
  const [projects, setProjects] = useState<Project[]>([])
  const [trends, setTrends] = useState<Trend[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showTour, setShowTour] = useState(false)

  useEffect(() => {
    loadDashboard()
  }, [])

  useEffect(() => {
    if (typeof window !== 'undefined' && !localStorage.getItem(ONBOARDING_KEY)) {
      setShowTour(true)
    }
  }, [])

  const dismissTour = () => {
    if (typeof window !== 'undefined') localStorage.setItem(ONBOARDING_KEY, '1')
    setShowTour(false)
  }

  async function loadDashboard() {
    setLoading(true)
    setError('')
    try {
      const [projectsRes, trendsRes]: any[] = await Promise.allSettled([
        api.getProjects(),
        api.getTrends(),
      ]).then((results) => results.map((r) => (r.status === 'fulfilled' ? r.value : null)))

      const projectList = projectsRes?.projects || projectsRes || []
      const list: Project[] = Array.isArray(projectList) ? projectList : []
      setProjects(list.slice(0, 5))
      setStats((prev) => [
        { ...prev[0], value: String(list.length || 0) },
        { ...prev[1], value: String(list.filter((p) => p.status === 'published').length || 0) },
        prev[2],
        prev[3],
      ])

      const trendList = trendsRes?.trends || trendsRes || []
      setTrends(Array.isArray(trendList) ? trendList.slice(0, 5) : [])
    } catch (err: any) {
      setError(err?.message || 'Could not load your dashboard.')
    } finally {
      setLoading(false)
    }
  }

  const isFirstRun = !loading && !error && projects.length === 0

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Welcome back! Here&apos;s your content overview.</p>
        </div>
        <Link
          href="/create/new"
          className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-medium hover:brightness-110 transition-all"
        >
          <Wand2 className="w-4 h-4" />
          Create Video
        </Link>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-destructive/10 text-destructive text-sm flex items-center justify-between gap-3 flex-wrap">
          <span className="flex items-center gap-2"><AlertCircle className="w-4 h-4" /> {error}</span>
          <button
            onClick={loadDashboard}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-destructive/10 hover:bg-destructive/20 font-medium transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      )}

      {showTour && (
        <div className="p-4 rounded-2xl border border-violet-500/30 bg-violet-500/5 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <Sparkles className="w-5 h-5 text-violet-500 shrink-0" />
            <div>
              <p className="text-sm font-medium">New here? Take the 1-minute tour</p>
              <p className="text-xs text-muted-foreground">We&apos;ll help you get your first video made.</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/onboarding"
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 text-white text-sm font-medium hover:brightness-110 transition-all"
            >
              Start tour
            </Link>
            <button
              onClick={dismissTour}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {isFirstRun && (
        <section className="p-6 sm:p-8 rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-600/10 via-purple-600/10 to-pink-600/10">
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-5 h-5 text-violet-500" />
            <h2 className="text-lg font-semibold">Let&apos;s make your first video</h2>
          </div>
          <p className="text-sm text-muted-foreground max-w-2xl">
            No experience needed. Pick an idea and AI writes the script, plans the scenes, generates the
            visuals and renders the video for you.
          </p>

          <div className="grid sm:grid-cols-3 gap-3 my-6">
            {onboardingSteps.map((step, i) => (
              <div key={step.title} className="p-4 rounded-xl bg-card/60 border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <step.icon className="w-4 h-4 text-violet-500" />
                  <span className="text-xs font-semibold text-muted-foreground">STEP {i + 1}</span>
                </div>
                <p className="text-sm font-medium">{step.title}</p>
                <p className="text-xs text-muted-foreground mt-1">{step.desc}</p>
              </div>
            ))}
          </div>

          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <MousePointerClick className="w-3.5 h-3.5" /> Start with an idea
          </p>
          <div className="flex flex-wrap gap-2 mb-6">
            {VIDEO_IDEAS.slice(0, 6).map((idea) => (
              <Link
                key={idea}
                href={`/create/new?topic=${encodeURIComponent(idea)}`}
                className="px-3 py-2 rounded-full bg-card border border-border text-xs hover:border-violet-500/50 hover:text-violet-500 transition-colors"
              >
                {idea}
              </Link>
            ))}
          </div>

          <Link
            href="/create/new"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-medium hover:brightness-110 transition-all"
          >
            <Wand2 className="w-4 h-4" /> Create a video
          </Link>
        </section>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div key={stat.label} className="p-4 rounded-2xl bg-card border border-border">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-muted-foreground">{stat.label}</span>
              <stat.icon className={`w-5 h-5 ${stat.color}`} />
            </div>
            <p className="text-2xl font-bold">{stat.value}</p>
            <p className="text-xs text-muted-foreground mt-1">{stat.change}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 p-6 rounded-2xl bg-card border border-border">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Recent Projects</h2>
            <Link href="/content/projects" className="text-sm text-muted-foreground hover:text-foreground">
              View all
            </Link>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
          ) : projects.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground text-sm">No projects yet</p>
              <Link href="/create/new" className="text-violet-500 text-sm hover:underline mt-2 inline-block">Create your first video</Link>
            </div>
          ) : (
            <div className="space-y-3">
              {projects.map((project) => (
                <Link
                  key={project.id}
                  href={`/studio/editor?project=${project.id}`}
                  className="flex items-center justify-between p-3 rounded-xl bg-muted/50 hover:bg-muted transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-violet-500/10 flex items-center justify-center shrink-0">
                      <Video className="w-5 h-5 text-violet-500" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{project.name || project.title || 'Untitled'}</p>
                      <p className="text-xs text-muted-foreground">{project.platform || project.project_type || 'short_form'}</p>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full shrink-0 ${
                    project.status === 'published' ? 'bg-emerald-500/10 text-emerald-500' :
                    project.status === 'review' ? 'bg-amber-500/10 text-amber-500' :
                    project.status === 'generating' || project.status === 'rendering' ? 'bg-violet-500/10 text-violet-500' :
                    'bg-blue-500/10 text-blue-500'
                  }`}>
                    {project.status}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="p-6 rounded-2xl bg-card border border-border">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Trending Topics</h2>
            <Link href="/discover/trends" className="text-sm text-muted-foreground hover:text-foreground">
              View all
            </Link>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
          ) : trends.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground text-sm">No trends analyzed yet</p>
              <Link href="/discover/trends" className="text-violet-500 text-sm hover:underline mt-2 inline-block">Discover trends</Link>
            </div>
          ) : (
            <div className="space-y-3">
              {trends.map((trend, i) => (
                <Link
                  key={trend.id || i}
                  href={`/create/new?topic=${encodeURIComponent(trend.topic || '')}`}
                  className="block p-3 rounded-xl bg-muted/50 hover:bg-muted transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium truncate">{trend.topic}</p>
                    <span className="text-xs font-bold text-violet-500 shrink-0">{trend.score || '—'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">{trend.source || 'AI Analysis'}</span>
                    <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
                      <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-purple-500" style={{ width: `${trend.score || 0}%` }} />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="p-6 rounded-2xl bg-gradient-to-r from-violet-600/10 via-purple-600/10 to-pink-600/10 border border-violet-500/20">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shrink-0">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold">AI Recommendations</h3>
            <p className="text-sm text-muted-foreground">Create more educational content about trending topics for maximum engagement. Use the AI agents to generate scripts and storyboards automatically.</p>
          </div>
          <Link href="/create/new" className="px-4 py-2 rounded-lg bg-violet-500/10 text-violet-500 text-sm font-medium hover:bg-violet-500/20 transition-colors text-center shrink-0">
            Create Video
          </Link>
        </div>
      </div>
    </div>
  )
}
