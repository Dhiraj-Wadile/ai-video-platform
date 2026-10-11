'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Film, Loader2, AlertCircle, Sparkles, Wand2 } from 'lucide-react'
import { api } from '@/lib/api'

interface Scene {
  scene_number?: number
  duration?: number
  narration?: string
  visual_description?: string
  camera?: string
  transition?: string
  emotion?: string
  caption?: string
}

const STYLES = ['cinematic', 'educational', 'documentary', 'playful', 'moody']

export default function StoryboardPage() {
  const [projects, setProjects] = useState<any[]>([])
  const [projectId, setProjectId] = useState('')
  const [script, setScript] = useState('')
  const [style, setStyle] = useState('cinematic')
  const [scenes, setScenes] = useState<Scene[]>([])
  const [totalDuration, setTotalDuration] = useState(0)
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { loadProjects() }, [])

  async function loadProjects() {
    try {
      const data: any = await api.getProjects()
      const list = Array.isArray(data) ? data : (data.projects || [])
      setProjects(list)
      if (list.length > 0) setProjectId(list[0].id)
    } catch {
      setProjects([])
    } finally {
      setLoadingProjects(false)
    }
  }

  async function handleLoadScript() {
    if (!projectId) return
    setError('')
    try {
      const detail: any = await api.getProjectDetail(projectId)
      const content = detail?.script?.content || ''
      if (!content) {
        setError('This project has no script yet. Generate a script first, or paste one below.')
        return
      }
      setScript(content)
    } catch (err: any) {
      setError(err.message || 'Could not load the project script')
    }
  }

  async function handleGenerate() {
    if (!script.trim()) return
    setGenerating(true)
    setError('')
    try {
      const data: any = await api.generateStoryboard({ script, style })
      const next = Array.isArray(data.scenes) ? data.scenes : []
      setScenes(next)
      setTotalDuration(data.total_duration || 0)
    } catch (err: any) {
      setError(err.message || 'Storyboard generation failed')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Film className="w-6 h-6 text-violet-500" />
          Storyboard
        </h1>
        <p className="text-sm text-muted-foreground">Turn a script into scene-by-scene visual directions</p>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-destructive/10 text-destructive text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      )}

      <div className="p-4 rounded-2xl bg-card border border-border space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <label className="block flex-1 min-w-[200px]">
            <span className="text-xs font-medium text-muted-foreground">Project</span>
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              disabled={loadingProjects}
              className="w-full mt-1 px-3 py-2 rounded-lg bg-background border border-border text-sm"
            >
              {projects.length === 0 && <option value="">No projects yet</option>}
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name || 'Untitled'}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-medium text-muted-foreground">Style</span>
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="mt-1 px-3 py-2 rounded-lg bg-background border border-border text-sm"
            >
              {STYLES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>
          <button
            onClick={handleLoadScript}
            disabled={!projectId}
            className="px-3 py-2 rounded-lg border border-border text-sm hover:bg-accent disabled:opacity-50"
          >
            Load project script
          </button>
        </div>

        <textarea
          value={script}
          onChange={(e) => setScript(e.target.value)}
          rows={6}
          placeholder="Paste or load a script, then generate the storyboard"
          className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm resize-y"
        />

        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerate}
            disabled={generating || !script.trim()}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500 text-white text-sm font-medium hover:brightness-110 disabled:opacity-50"
          >
            {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            Generate storyboard
          </button>
          {projectId && (
            <Link
              href={`/studio/editor?project=${projectId}`}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-border text-sm hover:bg-accent"
            >
              <Wand2 className="w-3.5 h-3.5" /> Open scene studio
            </Link>
          )}
        </div>
      </div>

      {scenes.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-sm">{scenes.length} scenes</h2>
            <span className="text-xs text-muted-foreground">{totalDuration}s total</span>
          </div>
          {scenes.map((scene, i) => (
            <div key={i} className="p-4 rounded-2xl bg-card border border-border flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-violet-500/10 text-violet-500 flex items-center justify-center font-bold text-sm shrink-0">
                {scene.scene_number ?? i + 1}
              </div>
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{scene.duration ?? 0}s</span>
                  {scene.camera && <span>{scene.camera}</span>}
                  {scene.transition && <span>{scene.transition}</span>}
                  {scene.emotion && <span>{scene.emotion}</span>}
                </div>
                {scene.narration && <p className="text-sm">{scene.narration}</p>}
                {scene.visual_description && (
                  <p className="text-xs text-muted-foreground">{scene.visual_description}</p>
                )}
              </div>
            </div>
          ))}
          <p className="text-xs text-muted-foreground">
            This storyboard is a plan. Persisted scenes — with images you can regenerate — live in the{' '}
            <Link href={`/studio/editor?project=${projectId}`} className="text-violet-500 hover:underline">
              scene studio
            </Link>.
          </p>
        </div>
      )}
    </div>
  )
}
