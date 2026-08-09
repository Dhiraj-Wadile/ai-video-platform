import Link from 'next/link'
import { Sparkles, Video, Bot, TrendingUp, BarChart3, Wand2 } from 'lucide-react'

export default function RootPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg">VideoAI</span>
          </div>
          <nav className="flex items-center gap-4">
            <Link href="/auth/signin" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Sign In
            </Link>
            <Link href="/auth/signup" className="px-4 py-2 rounded-lg bg-violet-500 text-white text-sm font-medium hover:brightness-110 transition-all">
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      <section className="flex-1 flex items-center justify-center px-6 py-20">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-violet-500/10 text-violet-500 text-sm font-medium">
            <Bot className="w-4 h-4" />
            AI-Powered Video Automation
          </div>

          <h1 className="text-5xl md:text-7xl font-bold tracking-tight">
            Automate Your
            <span className="bg-gradient-to-r from-violet-500 via-purple-500 to-pink-500 bg-clip-text text-transparent"> Video Pipeline</span>
          </h1>

          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            From trend discovery to publishing — let AI handle scriptwriting, storyboarding, voice generation, visual creation, and quality checks. You just review and publish.
          </p>

          <div className="flex items-center justify-center gap-4">
            <Link
              href="/auth/signup"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-semibold text-lg hover:brightness-110 transition-all hover:scale-105"
            >
              <Wand2 className="w-5 h-5" />
              Start Creating Free
            </Link>
            <Link
              href="/"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl bg-card border border-border font-semibold text-lg hover:bg-accent transition-all"
            >
              View Demo
            </Link>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-16">
            {[
              { icon: TrendingUp, label: 'Trend Discovery', desc: 'Find viral topics' },
              { icon: Video, label: 'Script Generation', desc: 'AI-written scripts' },
              { icon: Bot, label: 'AI Agents', desc: 'Specialized AI workers' },
              { icon: BarChart3, label: 'Analytics', desc: 'Performance insights' },
            ].map(({ icon: Icon, label, desc }) => (
              <div key={label} className="p-5 rounded-2xl bg-card border border-border text-center space-y-3">
                <Icon className="w-10 h-10 mx-auto text-violet-500" />
                <p className="font-medium">{label}</p>
                <p className="text-sm text-muted-foreground">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-border px-6 py-6 text-center text-sm text-muted-foreground">
        AI Video Platform &copy; 2026
      </footer>
    </div>
  )
}
