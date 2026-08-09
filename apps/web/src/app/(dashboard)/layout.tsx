'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { Video, Sparkles, TrendingUp, BarChart3, Wand2, Calendar, Settings, Bot, Users, Film, Music, Type, LogOut, Instagram } from 'lucide-react'
import { useAppStore } from '@/lib/store'

const navSections = [
  {
    title: 'Discover',
    items: [
      { label: 'Trends', href: '/discover/trends', icon: TrendingUp },
      { label: 'Ideas', href: '/discover/ideas', icon: Sparkles },
      { label: 'Opportunities', href: '/discover/opportunities', icon: BarChart3 },
      { label: 'Instagram Reels', href: '/discover/instagram', icon: Instagram },
    ],
  },
  {
    title: 'Create',
    items: [
      { label: 'New Video', href: '/create/new', icon: Video },
      { label: 'Script', href: '/create/script', icon: Type },
      { label: 'Characters', href: '/create/characters', icon: Users },
      { label: 'Storyboard', href: '/create/storyboard', icon: Film },
    ],
  },
  {
    title: 'Studio',
    items: [
      { label: 'Editor', href: '/studio/editor', icon: Wand2 },
      { label: 'Assets', href: '/studio/assets', icon: Sparkles },
      { label: 'Audio', href: '/studio/audio', icon: Music },
      { label: 'Captions', href: '/studio/captions', icon: Type },
    ],
  },
  {
    title: 'Content',
    items: [
      { label: 'Projects', href: '/content/projects', icon: Video },
      { label: 'Calendar', href: '/content/calendar', icon: Calendar },
      { label: 'Published', href: '/content/published', icon: BarChart3 },
    ],
  },
  {
    title: 'Analytics',
    items: [
      { label: 'Overview', href: '/analytics/overview', icon: BarChart3 },
      { label: 'Videos', href: '/analytics/videos', icon: Video },
      { label: 'AI Insights', href: '/analytics/insights', icon: Bot },
    ],
  },
  {
    title: 'AI',
    items: [
      { label: 'Agents', href: '/ai/agents', icon: Bot },
      { label: 'Runs', href: '/ai/runs', icon: Sparkles },
      { label: 'Models', href: '/ai/models', icon: Settings },
      { label: 'Costs', href: '/ai/costs', icon: BarChart3 },
    ],
  },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, setUser, token } = useAppStore()

  useEffect(() => {
    if (!token) {
      router.push('/auth/signin')
    }
  }, [token, router])

  const handleLogout = () => {
    localStorage.removeItem('token')
    setUser(null)
    router.push('/auth/signin')
  }

  if (!token) return null

  return (
    <div className="flex h-screen">
      <aside className="w-64 border-r border-border bg-card flex flex-col">
        <div className="p-4 border-b border-border">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg">VideoAI</span>
              <p className="text-[10px] text-muted-foreground">AI Video Platform</p>
            </div>
          </Link>
        </div>

        <nav className="flex-1 overflow-y-auto p-3 space-y-4">
          {navSections.map((section) => (
            <div key={section.title}>
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider px-3 mb-2">
                {section.title}
              </p>
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const isActive = pathname === item.href
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                        isActive
                          ? 'text-foreground bg-accent font-medium'
                          : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                      }`}
                    >
                      <item.icon className="w-4 h-4" />
                      {item.label}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="p-3 border-t border-border space-y-1">
          {user && (
            <div className="px-3 py-2 text-sm">
              <p className="font-medium truncate">{user.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user.email}</p>
            </div>
          )}
          <Link
            href="/settings"
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            <Settings className="w-4 h-4" />
            Settings
          </Link>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-destructive hover:bg-accent transition-colors w-full"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
