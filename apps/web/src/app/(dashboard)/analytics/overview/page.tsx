'use client'

import { BarChart3, TrendingUp, Eye, Heart, MessageCircle, Share2, ArrowUpRight, ArrowDownRight } from 'lucide-react'

export default function AnalyticsOverviewPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-violet-500" />
          Analytics Overview
        </h1>
        <p className="text-sm text-muted-foreground">Track your content performance across platforms</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Views', value: '45.2K', change: '+12%', up: true, icon: Eye },
          { label: 'Total Likes', value: '3.8K', change: '+8%', up: true, icon: Heart },
          { label: 'Comments', value: '456', change: '+15%', up: true, icon: MessageCircle },
          { label: 'Shares', value: '1.2K', change: '+22%', up: true, icon: Share2 },
        ].map((stat) => (
          <div key={stat.label} className="p-4 rounded-2xl bg-card border border-border">
            <div className="flex items-center justify-between mb-2">
              <stat.icon className="w-5 h-5 text-muted-foreground" />
              <span className={`flex items-center gap-0.5 text-xs font-medium ${stat.up ? 'text-emerald-500' : 'text-red-500'}`}>
                {stat.up ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                {stat.change}
              </span>
            </div>
            <p className="text-2xl font-bold">{stat.value}</p>
            <p className="text-xs text-muted-foreground mt-1">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-card border border-border">
          <h2 className="font-semibold mb-4">Views Over Time</h2>
          <div className="flex items-end gap-2 h-48">
            {[1200, 1800, 2400, 3200, 2800, 4500, 5200, 4800, 6100, 7200, 8500, 9200].map((val, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-gradient-to-t from-violet-500 to-purple-500 rounded-t transition-all"
                  style={{ height: `${(val / 10000) * 100}%`, minHeight: '4px' }}
                />
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-2 text-[10px] text-muted-foreground">
            <span>Jan</span><span>Feb</span><span>Mar</span><span>Apr</span><span>May</span><span>Jun</span><span>Jul</span><span>Aug</span><span>Sep</span><span>Oct</span><span>Nov</span><span>Dec</span>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-card border border-border">
          <h2 className="font-semibold mb-4">Top Performing Videos</h2>
          <div className="space-y-3">
            {[
              { title: 'Startup Story', views: '25.1K', platform: 'TikTok' },
              { title: '5 Money Habits', views: '12.5K', platform: 'YouTube' },
              { title: 'AI Secrets', views: '8.2K', platform: 'Instagram' },
              { title: 'Study Abroad', views: '5.8K', platform: 'YouTube' },
              { title: 'Stock Tips', views: '3.6K', platform: 'TikTok' },
            ].map((video, i) => (
              <div key={i} className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground w-4">{i + 1}</span>
                  <div>
                    <p className="text-sm font-medium">{video.title}</p>
                    <p className="text-[10px] text-muted-foreground">{video.platform}</p>
                  </div>
                </div>
                <span className="text-sm font-medium">{video.views}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
