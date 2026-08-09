'use client'

import { Settings, User, Key, Bell, Shield, Palette } from 'lucide-react'

export default function SettingsPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="w-6 h-6 text-violet-500" />
          Settings
        </h1>
        <p className="text-sm text-muted-foreground">Manage your account and platform settings</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <nav className="space-y-1">
          {[
            { icon: User, label: 'Profile' },
            { icon: Key, label: 'API Keys' },
            { icon: Bell, label: 'Notifications' },
            { icon: Shield, label: 'Security' },
            { icon: Palette, label: 'Appearance' },
          ].map(({ icon: Icon, label }) => (
            <button key={label} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors text-left">
              <Icon className="w-4 h-4" /> {label}
            </button>
          ))}
        </nav>

        <div className="lg:col-span-3 space-y-4">
          <div className="p-6 rounded-2xl bg-card border border-border space-y-4">
            <h2 className="font-semibold">Profile</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Name</label>
                <input defaultValue="John Doe" className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-sm" />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Email</label>
                <input defaultValue="john@example.com" className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-sm" />
              </div>
            </div>
            <button className="px-4 py-2 rounded-xl bg-violet-500 text-white text-sm font-medium hover:brightness-110 transition-all">
              Save Changes
            </button>
          </div>

          <div className="p-6 rounded-2xl bg-card border border-border space-y-4">
            <h2 className="font-semibold">API Keys</h2>
            <div className="space-y-3">
              {['OpenAI', 'ElevenLabs', 'Anthropic'].map((provider) => (
                <div key={provider} className="flex items-center gap-3">
                  <span className="w-24 text-sm font-medium">{provider}</span>
                  <input type="password" placeholder="sk-..." className="flex-1 px-4 py-2.5 rounded-xl bg-background border border-border text-sm font-mono" />
                  <button className="px-3 py-2 rounded-xl bg-muted text-sm hover:bg-accent transition-colors">Test</button>
                </div>
              ))}
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-card border border-border space-y-4">
            <h2 className="font-semibold">Default Settings</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Default Duration</label>
                <select className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-sm">
                  <option>15 seconds</option>
                  <option selected>30 seconds</option>
                  <option>45 seconds</option>
                  <option>60 seconds</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Default Style</label>
                <select className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-sm">
                  <option selected>Educational</option>
                  <option>Comedy</option>
                  <option>Storytelling</option>
                  <option>Motivational</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Quality Mode</label>
                <select className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-sm">
                  <option>Cheap</option>
                  <option selected>Balanced</option>
                  <option>High Quality</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Default Platform</label>
                <select className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-sm">
                  <option selected>YouTube Shorts</option>
                  <option>Instagram Reels</option>
                  <option>TikTok</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
