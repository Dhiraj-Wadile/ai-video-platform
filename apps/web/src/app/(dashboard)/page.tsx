'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Video, TrendingUp, Sparkles, DollarSign, BarChart3, Wand2, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'

export default function DashboardPage() {
  const [stats, setStats] = useState([
    { label: 'Videos Created', value: '0', change: 'Loading...', icon: Video, color: 'text-violet-500' },
    { label: 'Videos Published', value: '0', change: 'Loading...', icon: TrendingUp, color: 'text-emerald-500' },
    { label: 'Generation Cost', value: '$0.00', change: 'Loading...', icon: DollarSign, color: 'text-amber-500' },
    { label: 'Total Views', value: '0', change: 'Loading...', icon: BarChart3, color: 'text-blue-500' },
  ])
  const [projects, setProjects] = useState<any[]>([])
  const [trends, setTrends] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboard()
  }, [])

  async function loadDashboard() {
    try {
      const [projectsRes, trendsRes]: any[] = await Promise.allSettled([
        api.getProjects(),
        api.getTrends(),
      ]).then((results) => results.map((r) => r.status === 'fulfilled' ? r.value : null))

      if (projectsRes) {
        const projectList = projectsRes.projects || projectsRes || []
        setProjects(Array.isArray(projectList) ? projectList.slice(0, 5) : [])
        setStats((prev) => [
          { ...prev[0], value: String(projectList.length || 0), change: 'Total projects' },
          { ...prev[1], value: String(projectList.filter((p: any) => p.status === 'published').length || 0), change: 'Published' },
          prev[2],
          prev[3],
        ])
      }

      if (trendsRes) {
        const trendList = trendsRes.trends || trendsRes || []
        setTrends(Array.isArray(trendList) ? trendList.slice(0, 5) : [])
      }
    } catch {
      // Dashboard loads with default data on error
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Welcome back! Here&apos;s your content overview.</p>
        </div>
        <Link
          href="/create/new"
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-medium hover:brightness-110 transition-all"
        >
          <Wand2 className="w-4 h-4" />
          Create Video
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
              {projects.map((project: any) => (
                <div key={project.id} className="flex items-center justify-between p-3 rounded-xl bg-muted/50 hover:bg-muted transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-violet-500/10 flex items-center justify-center">
                      <Video className="w-5 h-5 text-violet-500" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{project.name || project.title || 'Untitled'}</p>
                      <p className="text-xs text-muted-foreground">{project.platform || project.project_type || 'short_form'}</p>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    project.status === 'published' ? 'bg-emerald-500/10 text-emerald-500' :
                    project.status === 'review' ? 'bg-amber-500/10 text-amber-500' :
                    project.status === 'generating' || project.status === 'rendering' ? 'bg-violet-500/10 text-violet-500' :
                    'bg-blue-500/10 text-blue-500'
                  }`}>
                    {project.status}
                  </span>
                </div>
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
              {trends.map((trend: any, i: number) => (
                <div key={trend.id || i} className="p-3 rounded-xl bg-muted/50 hover:bg-muted transition-colors">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium">{trend.topic}</p>
                    <span className="text-xs font-bold text-violet-500">{trend.score || '—'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">{trend.source || 'AI Analysis'}</span>
                    <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
                      <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-purple-500" style={{ width: `${trend.score || 0}%` }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="p-6 rounded-2xl bg-gradient-to-r from-violet-600/10 via-purple-600/10 to-pink-600/10 border border-violet-500/20">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold">AI Recommendations</h3>
            <p className="text-sm text-muted-foreground">Create more educational content about trending topics for maximum engagement. Use the AI agents to generate scripts and storyboards automatically.</p>
          </div>
          <Link href="/discover/ideas" className="px-4 py-2 rounded-lg bg-violet-500/10 text-violet-500 text-sm font-medium hover:bg-violet-500/20 transition-colors">
            Get Ideas
          </Link>
        </div>
      </div>
    </div>
  )
}
