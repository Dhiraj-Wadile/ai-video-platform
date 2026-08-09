'use client'

import { Video, Eye, Heart, Clock } from 'lucide-react'

const videos = [
  { id: '1', title: '5 Money Habits', platform: 'YouTube Shorts', views: '12.5K', likes: '890', retention: '78%', duration: '30s' },
  { id: '2', title: 'AI Secrets', platform: 'Instagram Reels', views: '8.2K', likes: '650', retention: '82%', duration: '45s' },
  { id: '3', title: 'Startup Story', platform: 'TikTok', views: '25.1K', likes: '2.1K', retention: '85%', duration: '60s' },
  { id: '4', title: 'Study Abroad', platform: 'YouTube Shorts', views: '5.8K', likes: '420', retention: '72%', duration: '45s' },
  { id: '5', title: 'Stock Tips', platform: 'TikTok', views: '3.6K', likes: '280', retention: '68%', duration: '30s' },
]

export default function AnalyticsVideosPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Video className="w-6 h-6 text-violet-500" />
          Video Analytics
        </h1>
        <p className="text-sm text-muted-foreground">Performance metrics for each video</p>
      </div>

      <div className="space-y-3">
        {videos.map((video) => (
          <div key={video.id} className="p-5 rounded-2xl bg-card border border-border hover:border-violet-500/30 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-violet-500/10 flex items-center justify-center">
                  <Video className="w-6 h-6 text-violet-500" />
                </div>
                <div>
                  <h3 className="font-semibold">{video.title}</h3>
                  <p className="text-sm text-muted-foreground">{video.platform} &middot; {video.duration}</p>
                </div>
              </div>
              <div className="flex items-center gap-8">
                <div className="text-center">
                  <div className="flex items-center gap-1 text-sm font-medium"><Eye className="w-3.5 h-3.5 text-muted-foreground" /> {video.views}</div>
                  <p className="text-[10px] text-muted-foreground">Views</p>
                </div>
                <div className="text-center">
                  <div className="flex items-center gap-1 text-sm font-medium"><Heart className="w-3.5 h-3.5 text-muted-foreground" /> {video.likes}</div>
                  <p className="text-[10px] text-muted-foreground">Likes</p>
                </div>
                <div className="text-center">
                  <div className="flex items-center gap-1 text-sm font-medium"><Clock className="w-3.5 h-3.5 text-muted-foreground" /> {video.retention}</div>
                  <p className="text-[10px] text-muted-foreground">Retention</p>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
