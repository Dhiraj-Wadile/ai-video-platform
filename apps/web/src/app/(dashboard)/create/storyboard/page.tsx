'use client'

import { useState } from 'react'
import { Film, Plus, GripVertical, Trash2, Edit2, Clock, RefreshCw } from 'lucide-react'

const sampleScenes = [
  { id: '1', number: 1, duration: 3, narration: 'Did you know this mind-blowing fact?', visual: 'Dramatic close-up with neon lighting', camera: 'zoom_in', transition: 'fade', emotion: 'excitement' },
  { id: '2', number: 2, duration: 5, narration: 'Most people don\'t understand this concept.', visual: 'Wide shot of modern office', camera: 'pan_left', transition: 'crossfade', emotion: 'curiosity' },
  { id: '3', number: 3, duration: 7, narration: 'Here\'s the simple explanation.', visual: 'Split screen comparison', camera: 'static', transition: 'slide_left', emotion: 'revelation' },
  { id: '4', number: 4, duration: 5, narration: 'The most surprising fact is this.', visual: 'Cinematic reveal with particles', camera: 'push_in', transition: 'zoom', emotion: 'amazement' },
  { id: '5', number: 5, duration: 3, narration: 'Follow for more facts!', visual: 'Bold text overlay with effects', camera: 'static', transition: 'fade', emotion: 'enthusiasm' },
]

export default function StoryboardPage() {
  const [scenes, setScenes] = useState(sampleScenes)
  const [selectedScene, setSelectedScene] = useState<string | null>(null)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Film className="w-6 h-6 text-violet-500" />
            Storyboard
          </h1>
          <p className="text-sm text-muted-foreground">Scene-by-scene visual planning</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-3 py-2 rounded-xl bg-muted text-sm font-medium hover:bg-accent transition-colors">
            <RefreshCw className="w-4 h-4" /> Regenerate
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500/10 text-violet-500 font-medium hover:bg-violet-500/20 transition-colors text-sm">
            <Plus className="w-4 h-4" /> Add Scene
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-3">
          {scenes.map((scene) => (
            <div
              key={scene.id}
              className={`p-4 rounded-2xl bg-card border transition-all cursor-pointer ${
                selectedScene === scene.id ? 'border-violet-500/50 ring-1 ring-violet-500/20' : 'border-border hover:border-violet-500/30'
              }`}
              onClick={() => setSelectedScene(selectedScene === scene.id ? null : scene.id)}
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-violet-500/10 text-violet-500 flex items-center justify-center font-bold text-sm shrink-0">
                  {scene.number}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Clock className="w-3 h-3 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">{scene.duration}s</span>
                    <span className="text-xs text-muted-foreground">&middot;</span>
                    <span className="text-xs text-muted-foreground">{scene.camera}</span>
                    <span className="text-xs text-muted-foreground">&middot;</span>
                    <span className="text-xs text-muted-foreground">{scene.transition}</span>
                  </div>
                  <p className="text-sm font-medium mb-1">{scene.narration}</p>
                  <p className="text-xs text-muted-foreground">{scene.visual}</p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button className="p-1 rounded hover:bg-accent"><Edit2 className="w-3.5 h-3.5 text-muted-foreground" /></button>
                  <button className="p-1 rounded hover:bg-red-500/10"><Trash2 className="w-3.5 h-3.5 text-muted-foreground hover:text-red-500" /></button>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-4">
          <div className="p-4 rounded-2xl bg-card border border-border">
            <h2 className="font-semibold text-sm mb-3">Scene Details</h2>
            {selectedScene ? (
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Duration</label>
                  <input type="number" defaultValue={scenes.find(s => s.id === selectedScene)?.duration} className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Camera</label>
                  <select className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm">
                    <option>Static</option>
                    <option>Zoom In</option>
                    <option>Zoom Out</option>
                    <option>Pan Left</option>
                    <option>Pan Right</option>
                    <option>Push In</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Transition</label>
                  <select className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm">
                    <option>Fade</option>
                    <option>Crossfade</option>
                    <option>Slide Left</option>
                    <option>Zoom</option>
                    <option>Cut</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Emotion</label>
                  <select className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm">
                    <option>Excitement</option>
                    <option>Curiosity</option>
                    <option>Revelation</option>
                    <option>Amazement</option>
                    <option>Calm</option>
                  </select>
                </div>
                <button className="w-full py-2 rounded-lg bg-violet-500/10 text-violet-500 text-sm font-medium hover:bg-violet-500/20 transition-colors">
                  Regenerate Scene
                </button>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">Select a scene to edit</p>
            )}
          </div>

          <div className="p-4 rounded-2xl bg-card border border-border">
            <h2 className="font-semibold text-sm mb-2">Timeline</h2>
            <div className="space-y-1">
              {scenes.map((scene) => (
                <div key={scene.id} className="flex items-center gap-2 text-xs">
                  <span className="w-6 text-muted-foreground">{scene.number}</span>
                  <div className="flex-1 h-6 rounded bg-violet-500/10 border border-violet-500/20 relative overflow-hidden">
                    <div className="absolute inset-0 flex items-center px-2">
                      <span className="truncate">{scene.duration}s</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-2 text-right">
              Total: {scenes.reduce((sum, s) => sum + s.duration, 0)}s
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
