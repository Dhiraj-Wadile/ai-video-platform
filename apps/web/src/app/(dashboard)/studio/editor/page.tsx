'use client'

import { Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import {
  Film, Loader2, RefreshCw, AlertCircle, CheckCircle2, Save, Sparkles, ImageOff, ExternalLink,
} from 'lucide-react'
import { api } from '@/lib/api'
import { formatDuration } from '@/lib/utils'

interface Scene {
  id: string
  scene_number: number
  duration: number | null
  narration: string | null
  visual_description: string | null
  camera: string | null
  caption: string | null
  transition: string | null
  image_url: string | null
}

interface QualityProblem {
  severity?: string
  description?: string
  suggestion?: string
}

interface ProjectDetail {
  id: string
  name: string
  status: string
  script: { id: string | null; title: string | null; content: string | null }
  scenes: Scene[]
  video_url: string | null
  quality: {
    overall_score: number | null
    passed: boolean
    safe_to_publish: boolean
    problems: Array<QualityProblem | string> | null
  } | null
}

type SceneField = 'narration' | 'visual_description' | 'caption' | 'camera' | 'transition' | 'duration'

type Notice = { kind: 'error' | 'ok'; text: string }

const SAVE_DEBOUNCE_MS = 700

export default function EditorPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    }>
      <EditorStudio />
    </Suspense>
  )
}

function EditorStudio() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const projectId = searchParams.get('project')

  const [projects, setProjects] = useState<any[]>([])
  const [detail, setDetail] = useState<ProjectDetail | null>(null)
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [pendingScene, setPendingScene] = useState<string | null>(null)
  const [dirty, setDirty] = useState<Record<string, SceneField[]>>({})
  const [saved, setSaved] = useState<Record<string, boolean>>({})
  const [rerendering, setRerendering] = useState(false)

  const detailRef = useRef<ProjectDetail | null>(null)
  const dirtyRef = useRef<Record<string, SceneField[]>>({})
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

  useEffect(() => { detailRef.current = detail }, [detail])
  useEffect(() => { dirtyRef.current = dirty }, [dirty])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data: any = await api.getProjects()
        const list = data.projects || data || []
        if (!cancelled) setProjects(Array.isArray(list) ? list : [])
      } catch {
        if (!cancelled) setNotice({ kind: 'error', text: 'Could not load projects' })
      } finally {
        if (!cancelled) setLoadingProjects(false)
      }
    })()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!projectId && !loadingProjects && projects.length > 0) {
      router.replace(`/studio/editor?project=${projects[0].id}`)
    }
  }, [projectId, loadingProjects, projects, router])

  const loadDetail = useCallback(async (id: string) => {
    setLoadingDetail(true)
    try {
      const data: any = await api.getProjectDetail(id)
      setDetail(data)
    } catch (err: any) {
      setDetail(null)
      setNotice({ kind: 'error', text: err.message || 'Could not load project' })
    } finally {
      setLoadingDetail(false)
    }
  }, [])

  useEffect(() => {
    if (!projectId) return
    // Pending debounces belong to the previous project; drop them instead of firing a stale save.
    Object.values(timers.current).forEach(clearTimeout)
    timers.current = {}
    setDirty({})
    setSaved({})
    setNotice(null)
    loadDetail(projectId)
  }, [projectId, loadDetail])

  useEffect(() => () => {
    Object.values(timers.current).forEach(clearTimeout)
  }, [])

  const flushScene = useCallback(async (sceneId: string) => {
    const scene = detailRef.current?.scenes.find((s) => s.id === sceneId)
    const fields = dirtyRef.current[sceneId] || []
    if (!projectId || !scene || fields.length === 0) return

    const payload: Record<string, unknown> = {}
    fields.forEach((f) => { payload[f] = f === 'duration' ? scene.duration : (scene[f] ?? '') })

    try {
      await api.updateScene(projectId, sceneId, payload)
      // Only clear what was sent: edits made while the request was in flight must survive.
      setDirty((d) => {
        const remaining = (d[sceneId] || []).filter((f) => !fields.includes(f))
        setSaved((s) => ({ ...s, [sceneId]: remaining.length === 0 }))
        return { ...d, [sceneId]: remaining }
      })
    } catch (err: any) {
      setNotice({ kind: 'error', text: `Scene ${scene.scene_number} not saved: ${err.message}` })
    }
  }, [projectId])

  const onFieldChange = (scene: Scene, field: SceneField, value: string | number) => {
    setDetail((d) => {
      if (!d) return d
      return {
        ...d,
        scenes: d.scenes.map((s) => (s.id === scene.id ? { ...s, [field]: value } : s)),
      }
    })
    setSaved((s) => ({ ...s, [scene.id]: false }))
    setDirty((d) => ({ ...d, [scene.id]: [...new Set([...(d[scene.id] || []), field])] }))

    if (timers.current[scene.id]) clearTimeout(timers.current[scene.id])
    timers.current[scene.id] = setTimeout(() => flushScene(scene.id), SAVE_DEBOUNCE_MS)
  }

  const handleRegenerate = async (scene: Scene) => {
    if (!projectId) return
    setPendingScene(scene.id)
    setNotice(null)
    try {
      await api.regenerateScene(projectId, scene.id)
      await loadDetail(projectId)
      setNotice({ kind: 'ok', text: `Scene ${scene.scene_number} visual regenerated` })
    } catch (err: any) {
      setNotice({ kind: 'error', text: `Regeneration failed: ${err.message}` })
    } finally {
      setPendingScene(null)
    }
  }

  const handleRerender = async () => {
    if (!projectId) return
    setRerendering(true)
    setNotice(null)
    try {
      await api.recut(projectId)
      await loadDetail(projectId)
      setNotice({ kind: 'ok', text: 'Re-render complete' })
    } catch (err: any) {
      setNotice({ kind: 'error', text: `Re-render failed: ${err.message}` })
    } finally {
      setRerendering(false)
    }
  }

  const handleSelectProject = (id: string) => {
    router.push(`/studio/editor?project=${id}`)
  }

  /** Refresh must not drop edits that are still sitting in the debounce window. */
  const handleRefresh = async () => {
    if (!projectId) return
    const pending = Object.values(dirtyRef.current).flat()
    if (pending.length > 0) {
      const ok = window.confirm('You have unsaved edits. Save them now and then refresh?')
      if (ok) {
        for (const scene of detailRef.current?.scenes ?? []) {
          if ((dirtyRef.current[scene.id] || []).length > 0) await flushScene(scene.id)
        }
      } else {
        return
      }
    }
    Object.values(timers.current).forEach(clearTimeout)
    timers.current = {}
    setDirty({})
    setSaved({})
    await loadDetail(projectId)
  }

  if (loadingProjects) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <div className="p-6 space-y-4">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Film className="w-6 h-6 text-violet-500" /> Scene Studio
        </h1>
        <div className="p-12 rounded-2xl bg-card border border-border text-center">
          <Film className="w-12 h-12 mx-auto text-muted-foreground mb-3 opacity-50" />
          <p className="text-muted-foreground mb-3">No projects yet</p>
          <Link href="/create/new" className="text-violet-500 text-sm hover:underline">
            Generate your first video
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Film className="w-6 h-6 text-violet-500" /> Scene Studio
          </h1>
          <p className="text-sm text-muted-foreground">Review scenes, fix what looks wrong, re-render</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={projectId || ''}
            onChange={(e) => handleSelectProject(e.target.value)}
            className="px-3 py-2 rounded-xl bg-card border border-border text-sm"
          >
            {projects.map((p: any) => (
              <option key={p.id} value={p.id}>{p.name || 'Untitled'}</option>
            ))}
          </select>
          <button
            onClick={handleRefresh}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-border text-sm hover:bg-accent"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button
            onClick={handleRerender}
            disabled={rerendering || loadingDetail || !detail || detail.scenes.length === 0}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-violet-500 text-white text-sm font-medium hover:brightness-110 disabled:opacity-50"
          >
            {rerendering ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            Re-render
          </button>
        </div>
      </div>

      {notice && (
        <div className={`p-3 rounded-xl text-sm flex items-center gap-2 ${
          notice.kind === 'error' ? 'bg-destructive/10 text-destructive' : 'bg-emerald-500/10 text-emerald-500'
        }`}>
          {notice.kind === 'error' ? <AlertCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
          {notice.text}
        </div>
      )}

      {loadingDetail ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : !detail ? (
        <div className="p-12 rounded-2xl bg-card border border-border text-center text-muted-foreground">
          Select a project to open its scenes.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-4">
            <div className="p-4 rounded-2xl bg-card border border-border space-y-3">
              <h2 className="font-semibold text-sm">Preview</h2>
              {detail.video_url ? (
                <video src={detail.video_url} controls className="w-full rounded-xl bg-black" />
              ) : (
                <div className="aspect-[9/16] rounded-xl bg-muted/40 flex flex-col items-center justify-center text-muted-foreground">
                  <Film className="w-10 h-10 mb-2 opacity-50" />
                  <p className="text-xs">No rendered video yet</p>
                </div>
              )}
              {detail.video_url && (
                <a
                  href={detail.video_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-violet-500 hover:underline"
                >
                  <ExternalLink className="w-3 h-3" /> Open video
                </a>
              )}
            </div>

            <div className="p-4 rounded-2xl bg-card border border-border space-y-2">
              <h2 className="font-semibold text-sm">Quality review</h2>
              {detail.quality ? (
                <>
                  <div className="flex items-center gap-3">
                    <span className={`text-2xl font-bold ${detail.quality.passed ? 'text-emerald-500' : 'text-amber-500'}`}>
                      {detail.quality.overall_score ?? 0}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {detail.quality.passed ? 'Passed gate' : 'Below gate'}<br />
                      {detail.quality.safe_to_publish ? 'Safe to publish' : 'Not cleared to publish'}
                    </span>
                  </div>
                  {detail.quality.problems && detail.quality.problems.length > 0 && (
                    <ul className="space-y-1">
                      {detail.quality.problems.map((p, i) => (
                        <li key={i} className="text-xs text-muted-foreground">
                          • {typeof p === 'string'
                            ? p
                            : [p.severity, p.description].filter(Boolean).join(': ') || 'Unspecified issue'}
                          {typeof p !== 'string' && p.suggestion && (
                            <span className="block text-[11px] opacity-80">→ {p.suggestion}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              ) : (
                <p className="text-xs text-muted-foreground">No review recorded for this project yet.</p>
              )}
            </div>
          </div>

          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-sm">
                Scenes ({detail.scenes.length})
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  {formatDuration(detail.scenes.reduce((sum, s) => sum + (s.duration || 0), 0))} total
                </span>
              </h2>
              <span className="text-xs text-muted-foreground">Edits save automatically</span>
            </div>

            {detail.scenes.length === 0 ? (
              <div className="p-12 rounded-2xl bg-card border border-border text-center text-muted-foreground">
                <p className="mb-3">This project has no scenes yet.</p>
                <Link href="/create/new" className="text-violet-500 text-sm hover:underline">
                  Generate a video for this idea
                </Link>
              </div>
            ) : (
              detail.scenes.map((scene) => (
                <div key={scene.id} className="p-4 rounded-2xl bg-card border border-border space-y-3">
                  <div className="flex items-start gap-4">
                    <div className="w-20 h-28 rounded-lg overflow-hidden bg-muted/40 shrink-0 flex items-center justify-center">
                      {scene.image_url ? (
                        <img src={scene.image_url} alt={`Scene ${scene.scene_number}`} className="w-full h-full object-cover" />
                      ) : (
                        <ImageOff className="w-5 h-5 text-muted-foreground opacity-60" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold">Scene {scene.scene_number}</span>
                        <span className="text-xs text-muted-foreground">{scene.duration ?? 0}s</span>
                        {(dirty[scene.id] || []).length > 0 ? (
                          <span className="text-[10px] text-amber-500">Unsaved edits</span>
                        ) : saved[scene.id] ? (
                          <span className="flex items-center gap-1 text-[10px] text-emerald-500">
                            <Save className="w-3 h-3" /> Saved
                          </span>
                        ) : null}
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {scene.narration || scene.visual_description || 'No narration for this scene'}
                      </p>
                    </div>
                    <button
                      onClick={() => handleRegenerate(scene)}
                      disabled={pendingScene === scene.id}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs hover:bg-accent disabled:opacity-50 shrink-0"
                    >
                      {pendingScene === scene.id
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <Sparkles className="w-3.5 h-3.5" />}
                      Regenerate visual
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <label className="block">
                      <span className="text-xs font-medium text-muted-foreground">Narration</span>
                      <textarea
                        value={scene.narration || ''}
                        onChange={(e) => onFieldChange(scene, 'narration', e.target.value)}
                        rows={2}
                        className="w-full mt-1 px-3 py-2 rounded-lg bg-background border border-border text-sm resize-none"
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-medium text-muted-foreground">Visual direction</span>
                      <textarea
                        value={scene.visual_description || ''}
                        onChange={(e) => onFieldChange(scene, 'visual_description', e.target.value)}
                        rows={2}
                        className="w-full mt-1 px-3 py-2 rounded-lg bg-background border border-border text-sm resize-none"
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-medium text-muted-foreground">Caption</span>
                      <input
                        value={scene.caption || ''}
                        onChange={(e) => onFieldChange(scene, 'caption', e.target.value)}
                        className="w-full mt-1 px-3 py-2 rounded-lg bg-background border border-border text-sm"
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-medium text-muted-foreground">Camera</span>
                      <input
                        value={scene.camera || ''}
                        onChange={(e) => onFieldChange(scene, 'camera', e.target.value)}
                        className="w-full mt-1 px-3 py-2 rounded-lg bg-background border border-border text-sm"
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-medium text-muted-foreground">Transition</span>
                      <input
                        value={scene.transition || ''}
                        onChange={(e) => onFieldChange(scene, 'transition', e.target.value)}
                        className="w-full mt-1 px-3 py-2 rounded-lg bg-background border border-border text-sm"
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-medium text-muted-foreground">Duration (seconds)</span>
                      <input
                        type="number"
                        min={1}
                        max={30}
                        value={scene.duration ?? 3}
                        onChange={(e) => onFieldChange(scene, 'duration', Number(e.target.value))}
                        className="w-full mt-1 px-3 py-2 rounded-lg bg-background border border-border text-sm"
                      />
                    </label>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
