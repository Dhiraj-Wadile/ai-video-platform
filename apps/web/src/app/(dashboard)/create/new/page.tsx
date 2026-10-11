'use client'

import { Suspense, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Wand2, Sparkles, Loader2, Video, Clock, BarChart3, CheckCircle2, AlertCircle, Shuffle } from 'lucide-react'
import { api } from '@/lib/api'
import { VIDEO_IDEAS } from '@/lib/utils'

function NewVideoForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [topic, setTopic] = useState('')
  const [duration, setDuration] = useState('30s')
  const [style, setStyle] = useState('educational')
  const [platform, setPlatform] = useState('instagram_reels')
  const [generating, setGenerating] = useState(false)
  const [progress, setProgress] = useState<{ step: string; done: boolean }[]>([])
  const [percent, setPercent] = useState(0)
  const [stageMessage, setStageMessage] = useState('')
  const [createdProjectId, setCreatedProjectId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [limitHit, setLimitHit] = useState(false)

  useEffect(() => {
    const preset = searchParams.get('topic')
    if (preset) setTopic(preset)
  }, [searchParams])

  const steps = [
    'Creating project...',
    'Generating AI script...',
    'Planning storyboard...',
    'Generating scene visuals...',
    'Rendering video...',
    'Finalizing...',
  ]

  const stepThresholds = [0, 5, 16, 31, 61, 96]

  const updateProgress = (value: number, completed: boolean) => {
    const safe = Math.max(0, Math.min(100, value ?? 0))
    setPercent(completed ? 100 : safe)
    setProgress((p) => p.map((s, i) => ({ ...s, done: completed || safe >= stepThresholds[i] })))
  }

  const handleGenerate = async () => {
    if (!topic.trim()) return
    setGenerating(true)
    setError('')
    setLimitHit(false)
    setProgress(steps.map((step) => ({ step, done: false })))

    try {
      // Step 1: Create project
      const project: any = await api.createProject({
        name: topic,
        description: `AI-generated video about ${topic}`,
        project_type: style === 'comedy' ? 'comedy' : style === 'storytelling' ? 'storytelling' : 'short_form',
        platform,
      })
      setProgress((p) => p.map((s, i) => i === 0 ? { ...s, done: true } : s))
      setCreatedProjectId(project.id)

      // Step 2: Start render pipeline
      const result: any = await api.startRender({
        project_id: project.id,
        topic,
        duration,
        style,
      })

      // Async mode: poll real progress; sync mode completes immediately.
      if (result.status === 'queued' && result.job_id) {
        setProgress((p) => p.map((s, i) => i === 1 ? { ...s, done: false } : s))
        for (let i = 0; i < 300; i++) {
          await new Promise((resolve) => setTimeout(resolve, 2000))
          const status: any = await api.getRenderStatus(result.job_id)

          if (status.status === 'completed') {
            updateProgress(100, true)
            router.push(`/studio/editor?project=${project.id}`)
            return
          }
          if (status.status === 'failed') {
            setError('Render failed: ' + (status.error || 'unknown error'))
            setProgress((p) => p.map((s) => ({ ...s, done: false })))
            setGenerating(false)
            return
          }
          if (status.progress_message) setStageMessage(status.progress_message)
          updateProgress(status.progress ?? 0, false)
        }
        setError('Render is taking longer than expected. Open the project to check on it.')
        setGenerating(false)
        return
      } else {
        updateProgress(100, true)
        setTimeout(() => {
          router.push(`/studio/editor?project=${project.id}`)
        }, 1200)
      }
    } catch (err: any) {
      setError(err.message || 'Generation failed')
      setLimitHit(err?.status === 402)
      setProgress((p) => p.map((s) => ({ ...s, done: false })))
    } finally {
      setGenerating(false)
    }
  }

  const surpriseMe = () => {
    const pick = VIDEO_IDEAS[Math.floor(Math.random() * VIDEO_IDEAS.length)]
    setTopic(pick)
  }

  return (
    <div className="p-4 sm:p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Wand2 className="w-6 h-6 text-violet-500" />
          Create New Video
        </h1>
        <p className="text-sm text-muted-foreground">Let AI generate a complete video from your idea</p>
      </div>

      <div className="p-4 sm:p-6 rounded-2xl bg-card border border-border space-y-6">
        {error && (
          <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm flex items-center gap-2 flex-wrap">
            <AlertCircle className="w-4 h-4" /> {error}
            {limitHit && (
              <Link href="/billing" className="text-violet-500 hover:underline font-medium">
                Upgrade plan
              </Link>
            )}
            {createdProjectId && (
              <Link
                href={`/studio/editor?project=${createdProjectId}`}
                className="text-violet-500 hover:underline font-medium"
              >
                Open project
              </Link>
            )}
          </div>
        )}

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium">Video Topic *</label>
            <button
              type="button"
              onClick={surpriseMe}
              className="inline-flex items-center gap-1.5 text-xs text-violet-500 hover:underline"
            >
              <Shuffle className="w-3.5 h-3.5" /> Surprise me
            </button>
          </div>
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., 5 habits that make you successful, Why AI is the future..."
            className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-violet-500 focus:ring-1 focus:ring-violet-500 outline-none transition-all text-sm"
          />
          <div className="flex flex-wrap gap-2 mt-3">
            {VIDEO_IDEAS.slice(0, 4).map((idea) => (
              <button
                key={idea}
                type="button"
                onClick={() => setTopic(idea)}
                className="px-3 py-1.5 rounded-full bg-muted/50 border border-border text-xs hover:border-violet-500/50 hover:text-violet-500 transition-colors"
              >
                {idea}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Duration</label>
            <select
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-violet-500 outline-none text-sm"
            >
              <option value="15s">15 seconds</option>
              <option value="30s">30 seconds</option>
              <option value="45s">45 seconds</option>
              <option value="60s">60 seconds</option>
              <option value="90s">90 seconds</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">Style</label>
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-violet-500 outline-none text-sm"
            >
              <option value="educational">Educational</option>
              <option value="comedy">Comedy</option>
              <option value="storytelling">Storytelling</option>
              <option value="motivational">Motivational</option>
              <option value="news">News/Current Events</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">Platform</label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-violet-500 outline-none text-sm"
            >
              <option value="instagram_reels">Instagram Reels</option>
              <option value="youtube_shorts">YouTube Shorts</option>
              <option value="tiktok">TikTok</option>
            </select>
          </div>
        </div>

        {generating && progress.length > 0 && (
          <div className="space-y-3">
            <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-violet-500 to-purple-500 rounded-full transition-all duration-500"
                style={{ width: `${percent}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{stageMessage || steps.find((_, i) => !progress[i]?.done) || 'Working...'}</span>
              <span>{percent}%</span>
            </div>
            <div className="space-y-2">
              {progress.map((step, i) => (
                <div key={i} className="flex items-center gap-3 text-sm">
                  {step.done ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <Loader2 className="w-4 h-4 animate-spin text-violet-500" />
                  )}
                  <span className={step.done ? 'text-muted-foreground line-through' : ''}>{step.step}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={handleGenerate}
          disabled={generating || !topic.trim()}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-medium hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {generating ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Generating Video...</>
          ) : (
            <><Sparkles className="w-4 h-4" /> Generate Video</>
          )}
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { icon: Video, label: 'Script', desc: 'AI writes the script' },
          { icon: Clock, label: 'Storyboard', desc: 'Scene-by-scene plan' },
          { icon: BarChart3, label: 'Quality Check', desc: 'AI reviews quality' },
        ].map(({ icon: Icon, label, desc }) => (
          <div key={label} className="p-4 rounded-2xl bg-card border border-border text-center">
            <Icon className="w-8 h-8 mx-auto text-violet-500 mb-2" />
            <p className="text-sm font-medium">{label}</p>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function NewVideoPage() {
  return (
    <Suspense fallback={<div className="p-6 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>}>
      <NewVideoForm />
    </Suspense>
  )
}
