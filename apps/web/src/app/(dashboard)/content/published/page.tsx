'use client'

import { Video, ExternalLink, Eye, Heart, MessageCircle, Share2 } from 'lucide-react'

const publishedVideos = [
  { id: '1', title: '5 Money Habits', platform: 'YouTube Shorts', views: '12.5K', likes: '890', comments: '45', shares: '120', published: '2 hours ago', url: '#' },
  { id: '2', title: 'AI Secrets', platform: 'Instagram Reels', views: '8.2K', likes: '650', comments: '32', shares: '88', published: '1 day ago', url: '#' },
  { id: '3', title: 'Startup Story', platform: 'TikTok', views: '25.1K', likes: '2.1K', comments: '156', shares: '430', published: '3 days ago', url: '#' },
]

export default function PublishedPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Video className="w-6 h-6 text-violet-500" />
          Published Videos
        </h1>
        <p className="text-sm text-muted-foreground">Track your published content across platforms</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Total Views</p>
          <p className="text-2xl font-bold">45.8K</p>
          <p className="text-xs text-emerald-500 mt-1">+12K this week</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Total Engagement</p>
          <p className="text-2xl font-bold">4.2K</p>
          <p className="text-xs text-emerald-500 mt-1">+800 this week</p>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border">
          <p className="text-sm text-muted-foreground mb-1">Platforms</p>
          <p className="text-2xl font-bold">3</p>
          <p className="text-xs text-muted-foreground mt-1">YouTube, Instagram, TikTok</p>
        </div>
      </div>

      <div className="space-y-3">
        {publishedVideos.map((video) => (
          <div key={video.id} className="p-5 rounded-2xl bg-card border border-border hover:border-violet-500/30 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-violet-500/10 flex items-center justify-center">
                  <Video className="w-6 h-6 text-violet-500" />
                </div>
                <div>
                  <h3 className="font-semibold">{video.title}</h3>
                  <p className="text-sm text-muted-foreground">{video.platform} &middot; {video.published}</p>
                </div>
              </div>
              <a href={video.url} className="p-2 rounded-lg hover:bg-accent transition-colors">
                <ExternalLink className="w-4 h-4 text-muted-foreground" />
              </a>
            </div>
            <div className="flex items-center gap-6 mt-3 pt-3 border-t border-border">
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground"><Eye className="w-3.5 h-3.5" /> {video.views}</span>
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground"><Heart className="w-3.5 h-3.5" /> {video.likes}</span>
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground"><MessageCircle className="w-3.5 h-3.5" /> {video.comments}</span>
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground"><Share2 className="w-3.5 h-3.5" /> {video.shares}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
