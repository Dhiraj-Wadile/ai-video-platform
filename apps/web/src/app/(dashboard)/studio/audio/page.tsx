'use client'

import { useState } from 'react'
import { Music, Play, Pause, Volume2, Plus, Search } from 'lucide-react'

const musicTracks = [
  { id: '1', name: 'Energetic Beat', mood: 'energetic', duration: '0:30', bpm: 128 },
  { id: '2', name: 'Cinematic Tension', mood: 'cinematic', duration: '0:45', bpm: 90 },
  { id: '3', name: 'Chill Lo-Fi', mood: 'calm', duration: '1:00', bpm: 85 },
  { id: '4', name: 'Motivational Rise', mood: 'motivational', duration: '0:30', bpm: 110 },
  { id: '5', name: 'Mystery Unveil', mood: 'mysterious', duration: '0:40', bpm: 95 },
  { id: '6', name: 'Upbeat Fun', mood: 'energetic', duration: '0:25', bpm: 135 },
]

const sfxList = [
  { name: 'Whoosh', category: 'Transition' },
  { name: 'Pop', category: 'UI' },
  { name: 'Click', category: 'UI' },
  { name: 'Heartbeat', category: 'Emotion' },
  { name: 'Explosion', category: 'Impact' },
  { name: 'Camera Shutter', category: 'Effect' },
  { name: 'Money Cash', category: 'Effect' },
  { name: 'Typing', category: 'UI' },
]

export default function AudioPage() {
  const [playing, setPlaying] = useState<string | null>(null)
  const [musicVolume, setMusicVolume] = useState(15)
  const [sfxVolume, setSfxVolume] = useState(50)
  const [narrationVolume, setNarrationVolume] = useState(80)

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Music className="w-6 h-6 text-violet-500" />
          Audio
        </h1>
        <p className="text-sm text-muted-foreground">Manage music, sound effects, and audio levels</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="p-4 rounded-2xl bg-card border border-border">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-sm">Music Library</h2>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <input placeholder="Search music..." className="pl-8 pr-3 py-1.5 rounded-lg bg-background border border-border text-xs w-40" />
                </div>
                <button className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-violet-500/10 text-violet-500 text-xs font-medium hover:bg-violet-500/20">
                  <Plus className="w-3 h-3" /> Upload
                </button>
              </div>
            </div>
            <div className="space-y-1">
              {musicTracks.map((track) => (
                <div key={track.id} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-muted/50 transition-colors">
                  <button
                    onClick={() => setPlaying(playing === track.id ? null : track.id)}
                    className="w-8 h-8 rounded-full bg-violet-500/10 flex items-center justify-center hover:bg-violet-500/20 transition-colors"
                  >
                    {playing === track.id ? <Pause className="w-3.5 h-3.5 text-violet-500" /> : <Play className="w-3.5 h-3.5 text-violet-500 ml-0.5" />}
                  </button>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{track.name}</p>
                    <p className="text-[10px] text-muted-foreground">{track.mood} &middot; {track.bpm} BPM</p>
                  </div>
                  <span className="text-xs text-muted-foreground">{track.duration}</span>
                  <button className="px-2.5 py-1 rounded-lg bg-muted text-xs hover:bg-violet-500/10 hover:text-violet-500 transition-colors">
                    Use
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-card border border-border">
            <h2 className="font-semibold text-sm mb-3">Sound Effects</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {sfxList.map((sfx) => (
                <button key={sfx.name} className="p-3 rounded-xl bg-muted/50 border border-border hover:border-violet-500/20 transition-colors text-center">
                  <p className="text-sm font-medium">{sfx.name}</p>
                  <p className="text-[10px] text-muted-foreground">{sfx.category}</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="p-4 rounded-2xl bg-card border border-border space-y-4">
            <h2 className="font-semibold text-sm">Audio Levels</h2>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-muted-foreground">Narration</label>
                <span className="text-xs text-muted-foreground">{narrationVolume}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={narrationVolume}
                onChange={(e) => setNarrationVolume(Number(e.target.value))}
                className="w-full"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-muted-foreground">Music</label>
                <span className="text-xs text-muted-foreground">{musicVolume}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={musicVolume}
                onChange={(e) => setMusicVolume(Number(e.target.value))}
                className="w-full"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-muted-foreground">SFX</label>
                <span className="text-xs text-muted-foreground">{sfxVolume}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={sfxVolume}
                onChange={(e) => setSfxVolume(Number(e.target.value))}
                className="w-full"
              />
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-card border border-border">
            <h2 className="font-semibold text-sm mb-3">AI Music</h2>
            <p className="text-xs text-muted-foreground mb-3">Generate custom music with AI</p>
            <div className="space-y-2">
              <input placeholder="Describe the music mood..." className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm" />
              <select className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm">
                <option>30 seconds</option>
                <option>45 seconds</option>
                <option>60 seconds</option>
              </select>
              <button className="w-full py-2 rounded-lg bg-violet-500/10 text-violet-500 text-sm font-medium hover:bg-violet-500/20 transition-colors">
                Generate Music
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
