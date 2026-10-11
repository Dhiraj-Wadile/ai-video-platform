'use client'

import { useEffect, useState } from 'react'
import {
  Send, Youtube, Instagram, Music2, Clock, CheckCircle2, XCircle, AlertCircle,
  Loader2, Trash2, RefreshCw, Zap, FlaskConical,
} from 'lucide-react'
import { api } from '@/lib/api'

interface Platform {
  platform: string
  label: string
  configured: boolean
  mode: string
}

interface Job {
  id: string
  project_id: string
  platform: string
  status: string
  title?: string
  provider?: string
  published_url?: string
  scheduled_at?: string
  published_at?: string
  error?: string
}

interface Project {
  id: string
  name?: string
  status?: string
}

const platformIcons: Record<string, typeof Youtube> = {
  youtube: Youtube,
  tiktok: Music2,
  instagram: Instagram,
}

const statusStyles: Record<string, string> = {
  published: 'bg-emerald-500/10 text-emerald-500',
  scheduled: 'bg-blue-500/10 text-blue-500',
  queued: 'bg-blue-500/10 text-blue-500',
  publishing: 'bg-violet-500/10 text-violet-500',
  failed: 'bg-red-500/10 text-red-500',
  cancelled: 'bg-muted text-muted-foreground',
}

export default function PublishingPage() {
  const [platforms, setPlatforms] = useState<Platform[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const [projectId, setProjectId] = useState('')
  const [selected, setSelected] = useState<string[]>([])
  const [when, setWhen] = useState('')
  const [title, setTitle] = useState('')
  const [caption, setCaption] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => { loadAll() }, [])

  async function loadAll() {
    setLoading(true)
    setError('')
    try {
      const [platformRes, projectRes, jobRes]: any[] = await Promise.all([
        api.getPublishingPlatforms(),
        api.getProjects(),
        api.getPublishingJobs(),
      ])
      setPlatforms(platformRes.platforms || [])
      const list = projectRes.projects || projectRes || []
      const projectList: Project[] = Array.isArray(list) ? list : []
      setProjects(projectList)
      if (projectList[0]) setProjectId((prev) => prev || projectList[0].id)
      setJobs(Array.isArray(jobRes) ? jobRes : [])
    } catch (err: any) {
      setError(err?.message || 'Could not load publishing data.')
    } finally {
      setLoading(false)
    }
  }

  async function refreshJobs() {
    try {
      const jobRes: any = await api.getPublishingJobs()
      setJobs(Array.isArray(jobRes) ? jobRes : [])
    } catch {
      // keep existing list
    }
  }

  function togglePlatform(name: string) {
    setSelected((prev) => prev.includes(name) ? prev.filter((p) => p !== name) : [...prev, name])
  }

  async function handleSchedule(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId || selected.length === 0) return
    setSubmitting(true)
    setError('')
    setNotice('')
    try {
      const payload: any = {
        project_id: projectId,
        platforms: selected,
        title: title || undefined,
        caption: caption || undefined,
      }
      if (when) payload.scheduled_at = new Date(when).toISOString()
      const created = (await api.schedulePublish(payload)) as Job[]
      const published = created.filter((j) => j.status === 'published').length
      const scheduled = created.filter((j) => j.status === 'scheduled').length
      setNotice(
        published > 0
          ? `Published to ${published} platform${published > 1 ? 's' : ''}${scheduled ? `, ${scheduled} scheduled` : ''}.`
          : `Scheduled for ${scheduled} platform${scheduled > 1 ? 's' : ''}.`
      )
      setTitle('')
      setCaption('')
      setWhen('')
      setSelected([])
      await refreshJobs()
    } catch (err: any) {
      setError(err?.message || 'Could not schedule the post.')
    } finally {
      setSubmitting(false)
    }
  }

  async function runAction(fn: () => Promise<any>) {
    setError('')
    try {
      await fn()
      await refreshJobs()
    } catch (err: any) {
      setError(err?.message || 'Action failed.')
    }
  }

  const projectName = (id: string) => projects.find((p) => p.id === id)?.name || 'Untitled'

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Send className="w-6 h-6 text-violet-500" />
          Publishing
        </h1>
        <p className="text-sm text-muted-foreground">Post or schedule your finished videos to social platforms.</p>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-destructive/10 text-destructive text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}
      {notice && (
        <div className="p-4 rounded-2xl bg-emerald-500/10 text-emerald-500 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" /> {notice}
        </div>
      )}

      <div className="p-4 sm:p-6 rounded-2xl bg-card border border-border">
        <h2 className="font-semibold mb-4">Schedule a post</h2>
        {loading ? (
          <div className="flex justify-center py-6"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
        ) : projects.length === 0 ? (
          <p className="text-sm text-muted-foreground">Create a video first, then come back to publish it.</p>
        ) : (
          <form onSubmit={handleSchedule} className="space-y-4">
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Project</label>
                <select
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-background border border-border focus:border-violet-500 outline-none text-sm"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.name || 'Untitled'}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">When (leave empty to post now)</label>
                <input
                  type="datetime-local"
                  value={when}
                  onChange={(e) => setWhen(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-background border border-border focus:border-violet-500 outline-none text-sm"
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Platforms</label>
              <div className="flex flex-wrap gap-2">
                {platforms.map((p) => {
                  const Icon = platformIcons[p.platform] || Send
                  const active = selected.includes(p.platform)
                  return (
                    <button
                      type="button"
                      key={p.platform}
                      onClick={() => togglePlatform(p.platform)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-sm transition-colors ${
                        active ? 'border-violet-500 bg-violet-500/10 text-violet-500' : 'border-border hover:bg-accent'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {p.label}
                      {!p.configured && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-500">sim</span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Title</label>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Defaults to the project name"
                  className="w-full px-4 py-2.5 rounded-xl bg-background border border-border focus:border-violet-500 outline-none text-sm"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Caption</label>
                <input
                  value={caption}
                  onChange={(e) => setCaption(e.target.value)}
                  placeholder="Hashtags, tags, description..."
                  className="w-full px-4 py-2.5 rounded-xl bg-background border border-border focus:border-violet-500 outline-none text-sm"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting || !projectId || selected.length === 0}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-medium hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Working...</> : <><Send className="w-4 h-4" /> {when ? 'Schedule' : 'Publish now'}</>}
            </button>
          </form>
        )}
      </div>

      <div className="p-4 sm:p-6 rounded-2xl bg-card border border-border">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold">Posts</h2>
          <button onClick={refreshJobs} className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>

        {jobs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No posts yet. Schedule one above.</p>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => {
              const Icon = platformIcons[job.platform] || Send
              const status = statusStyles[job.status] || 'bg-muted text-muted-foreground'
              return (
                <div key={job.id} className="p-4 rounded-xl bg-muted/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-violet-500/10 flex items-center justify-center shrink-0">
                      <Icon className="w-5 h-5 text-violet-500" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{job.title || projectName(job.project_id)}</p>
                      <p className="text-xs text-muted-foreground flex items-center gap-2 flex-wrap">
                        <span className="capitalize">{job.platform}</span>
                        {job.provider === 'mock' && (
                          <span className="inline-flex items-center gap-1 text-amber-500"><FlaskConical className="w-3 h-3" /> simulated</span>
                        )}
                        {job.scheduled_at && <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" /> {new Date(job.scheduled_at).toLocaleString()}</span>}
                      </p>
                      {job.error && <p className="text-xs text-red-500 mt-1 break-words">{job.error}</p>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-xs px-2.5 py-1 rounded-full font-medium capitalize ${status}`}>{job.status}</span>
                    {job.published_url && job.status === 'published' && (
                      <a
                        href={job.published_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs px-2.5 py-1 rounded-lg border border-border hover:bg-accent transition-colors"
                      >
                        View
                      </a>
                    )}
                    {(job.status === 'scheduled' || job.status === 'failed') && (
                      <button
                        onClick={() => runAction(() => api.publishJobNow(job.id))}
                        className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg border border-border hover:bg-accent transition-colors"
                      >
                        <Zap className="w-3.5 h-3.5" /> Publish
                      </button>
                    )}
                    {job.status === 'scheduled' && (
                      <button
                        onClick={() => runAction(() => api.cancelPublishJob(job.id))}
                        className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg border border-border hover:bg-accent transition-colors"
                      >
                        <XCircle className="w-3.5 h-3.5" /> Cancel
                      </button>
                    )}
                    <button
                      onClick={() => runAction(() => api.deletePublishJob(job.id))}
                      className="text-muted-foreground hover:text-destructive transition-colors"
                      aria-label="Delete post"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
