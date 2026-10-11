'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Sparkles, ArrowRight, Check, Wand2, Shuffle } from 'lucide-react'
import { VIDEO_IDEAS, ONBOARDING_KEY } from '@/lib/utils'

const STYLES = [
  { id: 'educational', label: 'Educational', desc: 'Teach something clearly and fast' },
  { id: 'storytelling', label: 'Storytelling', desc: 'A narrative people follow to the end' },
  { id: 'comedy', label: 'Comedy', desc: 'Funny, punchy, made to be shared' },
]

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [topic, setTopic] = useState('')
  const [style, setStyle] = useState('educational')

  const finish = (goCreate: boolean) => {
    if (typeof window !== 'undefined') localStorage.setItem(ONBOARDING_KEY, '1')
    if (goCreate && topic.trim()) {
      router.push(`/create/new?topic=${encodeURIComponent(topic.trim())}`)
    } else {
      router.push('/dashboard')
    }
  }

  const steps = [
    {
      title: 'Welcome to VideoAI',
      body: 'Turn an idea into a finished, ready-to-post video in minutes. Here is how it works:',
      content: (
        <ul className="space-y-3 text-sm">
          {[
            'Describe your idea in one line',
            'AI writes the script and plans the scenes',
            'It generates visuals, narration and captions',
            'We render the final video — you publish it',
          ].map((t, i) => (
            <li key={t} className="flex items-center gap-3">
              <span className="w-6 h-6 rounded-full bg-violet-500/10 text-violet-500 flex items-center justify-center text-xs font-semibold">{i + 1}</span>
              {t}
            </li>
          ))}
        </ul>
      ),
      nextLabel: 'Get started',
      canNext: true,
    },
    {
      title: 'What do you want to make?',
      body: 'Pick a starting idea or type your own. You can change it any time.',
      content: (
        <div className="space-y-4">
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. 5 habits that make you successful"
            className="w-full px-4 py-3 rounded-xl bg-background border border-border focus:border-violet-500 focus:ring-1 focus:ring-violet-500 outline-none text-sm"
          />
          <div className="flex flex-wrap gap-2">
            {VIDEO_IDEAS.slice(0, 6).map((idea) => (
              <button
                key={idea}
                type="button"
                onClick={() => setTopic(idea)}
                className="text-xs px-3 py-1.5 rounded-full border border-border hover:bg-accent transition-colors"
              >
                {idea}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setTopic(VIDEO_IDEAS[Math.floor(Math.random() * VIDEO_IDEAS.length)])}
              className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-full border border-violet-500 text-violet-500 hover:bg-violet-500/10 transition-colors"
            >
              <Shuffle className="w-3 h-3" /> Surprise me
            </button>
          </div>
        </div>
      ),
      nextLabel: 'Continue',
      canNext: true,
    },
    {
      title: 'Pick a style',
      body: 'This shapes the script, pacing and visuals. Choose what fits your content.',
      content: (
        <div className="space-y-2">
          {STYLES.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setStyle(s.id)}
              className={`w-full text-left p-4 rounded-xl border transition-colors flex items-center justify-between ${
                style === s.id ? 'border-violet-500 bg-violet-500/10' : 'border-border hover:bg-accent'
              }`}
            >
              <div>
                <p className="font-medium text-sm">{s.label}</p>
                <p className="text-xs text-muted-foreground">{s.desc}</p>
              </div>
              {style === s.id && <Check className="w-4 h-4 text-violet-500" />}
            </button>
          ))}
        </div>
      ),
      nextLabel: topic.trim() ? 'Create my video' : 'Go to dashboard',
      canNext: true,
    },
  ]

  const current = steps[step]
  const isLast = step === steps.length - 1

  const onNext = () => {
    if (isLast) {
      finish(topic.trim().length > 0)
    } else {
      setStep((s) => s + 1)
    }
  }

  return (
    <div className="min-h-full flex items-center justify-center p-6">
      <div className="w-full max-w-lg">
        <div className="flex items-center justify-center gap-2 mb-6">
          {steps.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 rounded-full transition-all ${i <= step ? 'w-8 bg-violet-500' : 'w-4 bg-muted'}`}
            />
          ))}
        </div>

        <div className="p-6 sm:p-8 rounded-3xl bg-card border border-border">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center mb-4">
            {step === 0 ? <Sparkles className="w-6 h-6 text-white" /> : <Wand2 className="w-6 h-6 text-white" />}
          </div>
          <h1 className="text-xl sm:text-2xl font-bold">{current.title}</h1>
          <p className="text-sm text-muted-foreground mt-1 mb-6">{current.body}</p>

          {current.content}

          <div className="flex items-center justify-between gap-3 mt-8">
            <button
              onClick={() => finish(false)}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Skip
            </button>
            <div className="flex items-center gap-2">
              {step > 0 && (
                <button
                  onClick={() => setStep((s) => s - 1)}
                  className="px-4 py-2.5 rounded-xl border border-border text-sm hover:bg-accent transition-colors"
                >
                  Back
                </button>
              )}
              <button
                onClick={onNext}
                disabled={!current.canNext}
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-medium text-sm hover:brightness-110 transition-all disabled:opacity-50"
              >
                {current.nextLabel}
                {isLast && topic.trim() ? <Wand2 className="w-4 h-4" /> : <ArrowRight className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
