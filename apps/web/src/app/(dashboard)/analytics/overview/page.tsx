'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { BarChart3, Eye, Heart, MessageCircle, Share2, Loader2, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { formatCount } from '@/lib/utils'

interface VideoStat {
  project_id: string
  title: string
  platform: string | null
  views: number
  likes: number
  comments: number
  shares: number
  engagement_rate: number
  fetched_at: string | null
}

interface Analytics {
  total_views: number
  total_likes: number
  total_comments: number
  total_shares: number
  video_count: number
  engagement_rate: number
  videos: VideoStat[]
}

export default function AnalyticsOverviewPage() {
  const [data, setData] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const res: any = await api.getAnalytics()
      setData({
        total_views: res.total_views || 0,
        total_likes: res.total_likes || 0,
        total_comments: res.total_comments || 0,
        total_shares: res.total_shares || 0,
        video_count: res.video_count || 0,
        engagement_rate: res.engagement_rate || 0,
        videos: Array.isArray(res.videos) ? res.videos : [],
      })
    } catch (err: any) {
      setError(err.message || 'Could not load analytics')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-violet-500" />
          Analytics Overview
        </h1>
        <p className="text-sm text-muted-foreground">Performance for the videos you generated</p>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-destructive/10 text-destructive text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Total Views', value: formatCount(data?.total_views), icon: Eye },
              { label: 'Likes', value: formatCount(data?.total_likes), icon: Heart },
              { label: 'Comments', value: formatCount(data?.total_comments), icon: MessageCircle },
              { label: 'Shares', value: formatCount(data?.total_shares), icon: Share2 },
            ].map((stat) => (
              <div key={stat.label} className="p-4 rounded-2xl bg-card border border-border">
                <div className="flex items-center justify-between mb-2">
                  <stat.icon className="w-5 h-5 text-muted-foreground" />
                </div>
                <p className="text-2xl font-bold">{stat.value}</p>
                <p className="text-xs text-muted-foreground mt-1">{stat.label}</p>
              </div>
            ))}
          </div>

          <div className="p-4 rounded-2xl bg-card border border-border flex flex-wrap items-center gap-6">
            <div>
              <p className="text-sm text-muted-foreground">Videos tracked</p>
              <p className="text-xl font-bold">{data?.video_count ?? 0}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Engagement rate</p>
              <p className="text-xl font-bold">{data?.engagement_rate ?? 0}%</p>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-card border border-border">
            <h2 className="font-semibold text-sm mb-4">Top performing videos</h2>
            {(data?.videos.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">
                No performance data recorded yet. Analytics appear once a video is published and metrics
                are fetched.{' '}
                <Link href="/content/projects" className="text-violet-500 hover:underline">View your projects</Link>
              </p>
            ) : (
              <div className="space-y-2">
                {data!.videos.map((video, i) => (
                  <div
                    key={`${video.project_id}-${video.fetched_at}`}
                    className="flex items-center justify-between p-3 rounded-xl hover:bg-muted/50"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-xs text-muted-foreground w-4 shrink-0">{i + 1}</span>
                      <div className="min-w-0">
                        <Link
                          href={`/studio/editor?project=${video.project_id}`}
                          className="text-sm font-medium hover:text-violet-500 truncate block"
                        >
                          {video.title}
                        </Link>
                        <p className="text-[10px] text-muted-foreground">
                          {video.platform || 'no platform set'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground shrink-0">
                      <span>{formatCount(video.views)} views</span>
                      <span>{video.engagement_rate}% eng.</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
