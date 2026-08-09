'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Wand2, Sparkles, Loader2, Video, Clock, BarChart3, CheckCircle2, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api'

export default function NewVideoPage() {
  const router = useRouter()
  const [topic, setTopic] = useState('')
  const [duration, setDuration] = useState('30s')
  const [style, setStyle] = useState('educational')
  const [platform, setPlatform] = useState('instagram_reels')
  const [generating, setGenerating] = useState(false)
  const [progress, setProgress] = useState<{ step: string; done: boolean }[]>([])
  const [error, setError] = useState('')

  const steps = [
    'Creating project...',
    'Generating AI script...',
    'Planning storyboard...',
    'Generating scene visuals...',
    'Rendering video...',
    'Finalizing...',
  ]

  const handleGenerate = async () => {
    if (!topic.trim()) return
    setGenerating(true)
    setError('')
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

      // Step 2-5: Start render pipeline
      const result: any = await api.startRender({
        project_id: project.id,
        topic,
        duration,
        style,
      })
      setProgress((p) => p.map((s) => ({ ...s, done: true })))

      // Success
      setTimeout(() => {
        router.push('/content/projects')
      }, 1500)
    } catch (err: any) {
      setError(err.message || 'Generation failed')
      setProgress((p) => p.map((s) => ({ ...s, done: false })))
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Wand2 className="w-6 h-6 text-violet-500" />
          Create New Video
        </h1>
        <p className="text-sm text-muted-foreground">Let AI generate a complete video from your idea</p>
      </div>

      <div className="p-6 rounded-2xl bg-card border border-border space-y-6">
        {error && (
          <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4" /> {error}
          </div>
        )}

        <div>
          <label className="text-sm font-medium mb-2 block">Video Topic *</label>
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., 5 habits that make you successful, Why AI is the future..."
            className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-violet-500 focus:ring-1 focus:ring-violet-500 outline-none transition-all text-sm"
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
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

      <div className="grid grid-cols-3 gap-4">
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
