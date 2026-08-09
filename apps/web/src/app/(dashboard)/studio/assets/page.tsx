'use client'

import { useState } from 'react'
import { Image, Upload, Trash2, Eye, Download, Grid, List } from 'lucide-react'

const assets = [
  { id: '1', name: 'Hook Scene Visual', type: 'image', url: '', created: '2 hours ago' },
  { id: '2', name: 'Setup Scene Visual', type: 'image', url: '', created: '2 hours ago' },
  { id: '3', name: 'Main Content Visual', type: 'image', url: '', created: '2 hours ago' },
  { id: '4', name: 'Thumbnail', type: 'image', url: '', created: '1 hour ago' },
  { id: '5', name: 'Narration Audio', type: 'audio', url: '', created: '2 hours ago' },
  { id: '6', name: 'Background Music', type: 'audio', url: '', created: '1 hour ago' },
]

export default function AssetsPage() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [filter, setFilter] = useState('all')

  const filteredAssets = assets.filter(a => filter === 'all' || a.type === filter)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Image className="w-6 h-6 text-violet-500" />
            Assets
          </h1>
          <p className="text-sm text-muted-foreground">Manage images, audio, and video assets</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500/10 text-violet-500 font-medium hover:bg-violet-500/20 transition-colors text-sm">
          <Upload className="w-4 h-4" /> Upload
        </button>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {['all', 'image', 'audio', 'video'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filter === f ? 'bg-violet-500/10 text-violet-500' : 'text-muted-foreground hover:bg-muted'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setViewMode('grid')} className={`p-1.5 rounded ${viewMode === 'grid' ? 'bg-muted' : ''}`}><Grid className="w-4 h-4" /></button>
          <button onClick={() => setViewMode('list')} className={`p-1.5 rounded ${viewMode === 'list' ? 'bg-muted' : ''}`}><List className="w-4 h-4" /></button>
        </div>
      </div>

      {viewMode === 'grid' ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredAssets.map((asset) => (
            <div key={asset.id} className="group rounded-2xl bg-card border border-border overflow-hidden hover:border-violet-500/30 transition-colors">
              <div className="aspect-square bg-muted flex items-center justify-center relative">
                <Image className="w-10 h-10 text-muted-foreground/40" />
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
                  <button className="w-8 h-8 rounded-full bg-white/90 text-black flex items-center justify-center hover:bg-white"><Eye className="w-3.5 h-3.5" /></button>
                  <button className="w-8 h-8 rounded-full bg-white/90 text-black flex items-center justify-center hover:bg-white"><Download className="w-3.5 h-3.5" /></button>
                  <button className="w-8 h-8 rounded-full bg-white/90 text-black flex items-center justify-center hover:bg-white"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>
              <div className="p-3">
                <p className="text-sm font-medium truncate">{asset.name}</p>
                <p className="text-[10px] text-muted-foreground">{asset.type} &middot; {asset.created}</p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-1">
          {filteredAssets.map((asset) => (
            <div key={asset.id} className="flex items-center gap-3 p-3 rounded-xl bg-card border border-border hover:border-violet-500/30 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center shrink-0">
                <Image className="w-5 h-5 text-muted-foreground/40" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{asset.name}</p>
                <p className="text-xs text-muted-foreground">{asset.type} &middot; {asset.created}</p>
              </div>
              <div className="flex items-center gap-1">
                <button className="p-1.5 rounded hover:bg-accent"><Eye className="w-4 h-4 text-muted-foreground" /></button>
                <button className="p-1.5 rounded hover:bg-accent"><Download className="w-4 h-4 text-muted-foreground" /></button>
                <button className="p-1.5 rounded hover:bg-red-500/10"><Trash2 className="w-4 h-4 text-muted-foreground hover:text-red-500" /></button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
