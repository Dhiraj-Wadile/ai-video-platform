'use client'

import { useState } from 'react'
import { Wand2, Play, Pause, SkipBack, SkipForward, Volume2, Download, Save, Undo, Redo, ZoomIn, ZoomOut, Plus, Trash2, Music, Type, Film, Image } from 'lucide-react'

const timelineTracks = [
  { id: 'video', label: 'Video', icon: Film, color: 'bg-violet-500', items: [
    { id: '1', start: 0, duration: 3, label: 'Hook Scene', color: 'bg-violet-500/30 border-violet-500' },
    { id: '2', start: 3, duration: 5, label: 'Setup Scene', color: 'bg-blue-500/30 border-blue-500' },
    { id: '3', start: 8, duration: 7, label: 'Main Content', color: 'bg-purple-500/30 border-purple-500' },
    { id: '4', start: 15, duration: 5, label: 'Payoff', color: 'bg-emerald-500/30 border-emerald-500' },
    { id: '5', start: 20, duration: 3, label: 'CTA', color: 'bg-amber-500/30 border-amber-500' },
  ]},
  { id: 'audio', label: 'Audio', icon: Music, color: 'bg-emerald-500', items: [
    { id: 'a1', start: 0, duration: 23, label: 'Narration', color: 'bg-emerald-500/30 border-emerald-500' },
    { id: 'a2', start: 0, duration: 23, label: 'Background Music', color: 'bg-teal-500/30 border-teal-500' },
  ]},
  { id: 'text', label: 'Text', icon: Type, color: 'bg-amber-500', items: [
    { id: 't1', start: 0, duration: 3, label: 'Hook Text', color: 'bg-amber-500/30 border-amber-500' },
    { id: 't2', start: 20, duration: 3, label: 'CTA Text', color: 'bg-orange-500/30 border-orange-500' },
  ]},
  { id: 'captions', label: 'Captions', icon: Type, color: 'bg-pink-500', items: [
    { id: 'c1', start: 0, duration: 23, label: 'Word Captions', color: 'bg-pink-500/30 border-pink-500' },
  ]},
]

export default function EditorPage() {
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [zoom, setZoom] = useState(1)
  const totalDuration = 23

  return (
    <div className="h-screen flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <h1 className="font-semibold text-sm">Video Editor</h1>
          <span className="text-xs text-muted-foreground">Untitled Project</span>
        </div>
        <div className="flex items-center gap-2">
          <button className="p-1.5 rounded hover:bg-accent transition-colors"><Undo className="w-4 h-4" /></button>
          <button className="p-1.5 rounded hover:bg-accent transition-colors"><Redo className="w-4 h-4" /></button>
          <div className="w-px h-5 bg-border mx-1" />
          <button className="p-1.5 rounded hover:bg-accent transition-colors"><Save className="w-4 h-4" /></button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-500 text-white text-xs font-medium hover:brightness-110 transition-all">
            <Download className="w-3.5 h-3.5" /> Export
          </button>
        </div>
      </div>

      <div className="flex-1 flex">
        <div className="flex-1 flex flex-col">
          <div className="flex-1 flex items-center justify-center bg-black/5 dark:bg-black/20 p-4">
            <div className="aspect-[9/16] max-h-full bg-muted rounded-xl overflow-hidden relative border border-border">
              <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Film className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-xs">Preview</p>
                  <p className="text-[10px] text-muted-foreground">{currentTime.toFixed(1)}s / {totalDuration}s</p>
                </div>
              </div>
            </div>
          </div>

          <div className="px-4 py-3 border-t border-border">
            <div className="flex items-center justify-center gap-3">
              <button className="p-1.5 rounded hover:bg-accent transition-colors"><SkipBack className="w-4 h-4" /></button>
              <button
                onClick={() => setPlaying(!playing)}
                className="w-10 h-10 rounded-full bg-violet-500 text-white flex items-center justify-center hover:brightness-110 transition-all"
              >
                {playing ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
              </button>
              <button className="p-1.5 rounded hover:bg-accent transition-colors"><SkipForward className="w-4 h-4" /></button>
              <div className="w-px h-5 bg-border mx-1" />
              <button className="p-1.5 rounded hover:bg-accent transition-colors"><Volume2 className="w-4 h-4" /></button>
            </div>
          </div>
        </div>

        <div className="w-72 border-l border-border bg-card p-4 space-y-4 overflow-y-auto">
          <h2 className="font-semibold text-sm">Properties</h2>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Scene</label>
              <div className="p-3 rounded-lg bg-muted/50 border border-border">
                <p className="text-sm font-medium">Hook Scene</p>
                <p className="text-xs text-muted-foreground mt-1">0s - 3s</p>
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Duration</label>
              <input type="number" defaultValue={3} className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Transition</label>
              <select className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm">
                <option>Fade</option>
                <option>Crossfade</option>
                <option>Slide Left</option>
                <option>Zoom</option>
                <option>Cut</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Camera</label>
              <select className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm">
                <option>Static</option>
                <option>Zoom In</option>
                <option>Zoom Out</option>
                <option>Pan Left</option>
                <option>Pan Right</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <div className="h-64 border-t border-border bg-card flex flex-col">
        <div className="flex items-center justify-between px-4 py-2 border-b border-border">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium">Timeline</span>
            <span className="text-xs text-muted-foreground">{totalDuration}s</span>
          </div>
          <div className="flex items-center gap-1">
            <button onClick={() => setZoom(Math.max(0.5, zoom - 0.25))} className="p-1 rounded hover:bg-accent"><ZoomOut className="w-3.5 h-3.5" /></button>
            <span className="text-xs text-muted-foreground w-12 text-center">{Math.round(zoom * 100)}%</span>
            <button onClick={() => setZoom(Math.min(3, zoom + 0.25))} className="p-1 rounded hover:bg-accent"><ZoomIn className="w-3.5 h-3.5" /></button>
          </div>
        </div>

        <div className="flex-1 overflow-x-auto overflow-y-auto p-2">
          <div className="space-y-1" style={{ minWidth: `${totalDuration * 50 * zoom}px` }}>
            {timelineTracks.map((track) => (
              <div key={track.id} className="flex items-center gap-1 h-8">
                <div className="w-20 shrink-0 flex items-center gap-1.5 px-2">
                  <track.icon className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground truncate">{track.label}</span>
                </div>
                <div className="flex-1 relative h-full bg-muted/30 rounded">
                  {track.items.map((item) => (
                    <div
                      key={item.id}
                      className={`absolute top-0.5 bottom-0.5 rounded border cursor-pointer hover:brightness-110 transition-all ${item.color}`}
                      style={{
                        left: `${(item.start / totalDuration) * 100}%`,
                        width: `${(item.duration / totalDuration) * 100}%`,
                      }}
                    >
                      <span className="text-[9px] px-1 py-0.5 truncate block">{item.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
