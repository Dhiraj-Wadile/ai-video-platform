'use client'

import { useState, useEffect } from 'react'
import { Video, FolderOpen, Plus, Clock, CheckCircle2, AlertCircle, Film, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'

const statusConfig: Record<string, { color: string; icon: typeof CheckCircle2 }> = {
  published: { color: 'bg-emerald-500/10 text-emerald-500', icon: CheckCircle2 },
  review: { color: 'bg-amber-500/10 text-amber-500', icon: Clock },
  approved: { color: 'bg-blue-500/10 text-blue-500', icon: CheckCircle2 },
  rendering: { color: 'bg-violet-500/10 text-violet-500', icon: Film },
  generating: { color: 'bg-violet-500/10 text-violet-500', icon: Film },
  scheduled: { color: 'bg-blue-500/10 text-blue-500', icon: Clock },
  draft: { color: 'bg-muted text-muted-foreground', icon: FolderOpen },
  failed: { color: 'bg-red-500/10 text-red-500', icon: AlertCircle },
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadProjects() }, [])

  async function loadProjects() {
    try {
      const data: any = await api.getProjects()
      const list = data.projects || data || []
      setProjects(Array.isArray(list) ? list : [])
    } catch {
      // Empty state on error
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this project?')) return
    try {
      await api.deleteProject(id)
      setProjects((prev) => prev.filter((p) => p.id !== id))
    } catch {
      // Handle error
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Video className="w-6 h-6 text-violet-500" />
            Projects
          </h1>
          <p className="text-sm text-muted-foreground">Manage all your video projects</p>
        </div>
        <Link
          href="/create/new"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500/10 text-violet-500 font-medium hover:bg-violet-500/20 transition-colors text-sm"
        >
          <Plus className="w-4 h-4" /> New Project
        </Link>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
      ) : projects.length === 0 ? (
        <div className="text-center py-12">
          <Video className="w-12 h-12 mx-auto text-muted-foreground mb-3 opacity-50" />
          <p className="text-muted-foreground mb-2">No projects yet</p>
          <Link href="/create/new" className="text-violet-500 text-sm hover:underline">Create your first video</Link>
        </div>
      ) : (
        <div className="space-y-3">
          {projects.map((project: any) => {
            const config = statusConfig[project.status] || statusConfig.draft
            const StatusIcon = config.icon
            return (
              <div key={project.id} className="p-5 rounded-2xl bg-card border border-border hover:border-violet-500/30 transition-colors cursor-pointer">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-violet-500/10 flex items-center justify-center">
                      <Video className="w-6 h-6 text-violet-500" />
                    </div>
                    <div>
                      <h3 className="font-semibold">{project.name || 'Untitled'}</h3>
                      <p className="text-sm text-muted-foreground">{project.platform || project.project_type || 'short_form'} &middot; {project.status}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={`flex items-center gap-1 text-xs px-3 py-1 rounded-full font-medium ${config.color}`}>
                      <StatusIcon className="w-3 h-3" />
                      {project.status}
                    </span>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(project.id) }}
                      className="text-xs text-muted-foreground hover:text-destructive transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
