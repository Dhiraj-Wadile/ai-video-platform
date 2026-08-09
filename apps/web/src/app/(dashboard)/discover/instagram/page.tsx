'use client'

import { useState } from 'react'
import { TrendingUp, Sparkles, Instagram, Music, Hash, Clock, Users, Zap, ArrowRight } from 'lucide-react'
import Link from 'next/link'

const trendingFormats = [
  {
    title: 'AI Explainers',
    description: 'Short educational clips about AI and tech',
    hooks: ['AI is replacing...', 'This AI tool will change...', 'You won\'t believe what AI can do...'],
    duration: '15-30s',
    engagement: 'High',
    color: 'from-violet-500 to-purple-600',
  },
  {
    title: 'Before/After Reveals',
    description: 'Show transformation or comparison',
    hooks: ['POV: You discover...', 'Watch this transformation...', 'From zero to hero in...'],
    duration: '7-15s',
    engagement: 'Very High',
    color: 'from-pink-500 to-rose-600',
  },
  {
    title: 'Listicle Hooks',
    description: 'Numbered tips or facts',
    hooks: ['3 things nobody tells you about...', 'Top 5 secrets of...', 'Day 1 of learning...'],
    duration: '30-60s',
    engagement: 'High',
    color: 'from-amber-500 to-orange-600',
  },
  {
    title: 'Story Time',
    description: 'Personal or fictional stories',
    hooks: ['So basically what happened was...', 'Story time: The day I...', 'This changed my life...'],
    duration: '30-90s',
    engagement: 'Medium-High',
    color: 'from-emerald-500 to-teal-600',
  },
  {
    title: 'Motivational Quotes',
    description: 'Inspirational content with visuals',
    hooks: ['Listen to this...', 'If you need motivation...', 'Remember this always...'],
    duration: '7-15s',
    engagement: 'Very High',
    color: 'from-blue-500 to-indigo-600',
  },
  {
    title: 'Trending Audio',
    description: 'Use trending sounds and music',
    hooks: ['When the beat drops...', 'POV: You finally...', 'The vibe is unmatched...'],
    duration: '7-30s',
    engagement: 'Very High',
    color: 'from-red-500 to-pink-600',
  },
]

const reelsTips = [
  { icon: Clock, tip: 'Post between 7-9 PM for max reach' },
  { icon: Hash, tip: 'Use 3-5 relevant hashtags, not more' },
  { icon: Music, tip: 'Trending audio boosts visibility by 40%' },
  { icon: Zap, tip: 'First 3 seconds determine 70% watch time' },
  { icon: Users, tip: 'Reply to comments within first hour' },
  { icon: Instagram, tip: 'Consistency: 1-3 Reels per day is optimal' },
]

export default function ReelsTrendingPage() {
  const [selectedFormat, setSelectedFormat] = useState<number | null>(null)

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Instagram className="w-6 h-6 text-pink-500" />
          Instagram Reels Trends
        </h1>
        <p className="text-sm text-muted-foreground">Optimize your content for maximum Instagram engagement</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-gradient-to-br from-pink-500/10 to-rose-500/10 border border-pink-500/20">
          <p className="text-sm text-muted-foreground mb-1">Trending Audio</p>
          <p className="text-xl font-bold">12 New</p>
          <p className="text-xs text-pink-500 mt-1">Updated 2h ago</p>
        </div>
        <div className="p-4 rounded-2xl bg-gradient-to-br from-violet-500/10 to-purple-500/10 border border-violet-500/20">
          <p className="text-sm text-muted-foreground mb-1">Best Posting Times</p>
          <p className="text-xl font-bold">7-9 PM</p>
          <p className="text-xs text-violet-500 mt-1">Your timezone</p>
        </div>
        <div className="p-4 rounded-2xl bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border border-emerald-500/20">
          <p className="text-sm text-muted-foreground mb-1">Avg Engagement</p>
          <p className="text-xl font-bold">4.2%</p>
          <p className="text-xs text-emerald-500 mt-1">+0.8% this week</p>
        </div>
      </div>

      <div className="p-5 rounded-2xl bg-card border border-border">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-amber-500" />
          Quick Tips for Viral Reels
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {reelsTips.map((item, i) => (
            <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-muted/50">
              <item.icon className="w-4 h-4 text-pink-500 mt-0.5 shrink-0" />
              <p className="text-sm">{item.tip}</p>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-violet-500" />
          Trending Reels Formats
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {trendingFormats.map((format, i) => (
            <div
              key={i}
              onClick={() => setSelectedFormat(selectedFormat === i ? null : i)}
              className={`p-5 rounded-2xl bg-card border transition-all cursor-pointer ${
                selectedFormat === i ? 'border-violet-500 ring-1 ring-violet-500/20' : 'border-border hover:border-violet-500/30'
              }`}
            >
              <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${format.color} flex items-center justify-center mb-3`}>
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <h3 className="font-semibold mb-1">{format.title}</h3>
              <p className="text-sm text-muted-foreground mb-3">{format.description}</p>
              <div className="flex items-center gap-3 text-xs text-muted-foreground mb-3">
                <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {format.duration}</span>
                <span className="flex items-center gap-1"><TrendingUp className="w-3 h-3" /> {format.engagement}</span>
              </div>
              {selectedFormat === i && (
                <div className="space-y-2 border-t border-border pt-3">
                  <p className="text-xs font-medium text-muted-foreground">Hook Ideas:</p>
                  {format.hooks.map((hook, j) => (
                    <p key={j} className="text-sm italic text-muted-foreground">&ldquo;{hook}&rdquo;</p>
                  ))}
                  <Link
                    href={`/create/new?topic=${encodeURIComponent(format.title)}&style=storytelling`}
                    className="flex items-center gap-1 text-sm text-violet-500 hover:underline mt-2"
                  >
                    Create Video <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="p-6 rounded-2xl bg-gradient-to-r from-pink-600/10 via-violet-600/10 to-purple-600/10 border border-pink-500/20">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-pink-500 to-violet-600 flex items-center justify-center">
            <Instagram className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold">Auto-Optimize for Instagram</h3>
            <p className="text-sm text-muted-foreground">Generate videos with Reels-optimized aspect ratio (9:16), captions, hooks, and trending elements automatically.</p>
          </div>
          <Link href="/create/new?platform=instagram_reels" className="px-4 py-2 rounded-lg bg-pink-500/10 text-pink-500 text-sm font-medium hover:bg-pink-500/20 transition-colors">
            Create Reel
          </Link>
        </div>
      </div>
    </div>
  )
}
