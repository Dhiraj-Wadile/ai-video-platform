'use client'

import { useState } from 'react'
import { Type, Plus, Palette, Move, Eye } from 'lucide-react'

const captionPresets = [
  { name: 'Minimal', font: 'Arial', size: 42, color: '#FFFFFF', animation: 'fade' },
  { name: 'Comedy', font: 'Impact', size: 56, color: '#FFD700', animation: 'pop' },
  { name: 'Meme', font: 'Impact', size: 60, color: '#FFFFFF', animation: 'pop' },
  { name: 'Podcast', font: 'Georgia', size: 38, color: '#E0E0E0', animation: 'fade' },
  { name: 'Gaming', font: 'monospace', size: 44, color: '#00FF00', animation: 'highlight' },
  { name: 'News', font: 'Arial', size: 40, color: '#FFFFFF', animation: 'slide' },
  { name: 'Story', font: 'Georgia', size: 46, color: '#FFFFFF', animation: 'highlight' },
]

const sampleCaptions = [
  { word: 'Did', start: 0, end: 0.3, highlighted: false },
  { word: 'you', start: 0.3, end: 0.5, highlighted: false },
  { word: 'know', start: 0.5, end: 0.8, highlighted: true },
  { word: 'this', start: 0.8, end: 1.0, highlighted: false },
  { word: 'mind-blowing', start: 1.0, end: 1.5, highlighted: false },
  { word: 'fact?', start: 1.5, end: 1.8, highlighted: true },
]

export default function CaptionsPage() {
  const [selectedPreset, setSelectedPreset] = useState('minimal')
  const [fontSize, setFontSize] = useState(48)
  const [fontColor, setFontColor] = useState('#FFFFFF')
  const [position, setPosition] = useState('bottom')

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Type className="w-6 h-6 text-violet-500" />
          Captions
        </h1>
        <p className="text-sm text-muted-foreground">Configure and style your video captions</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="p-4 rounded-2xl bg-card border border-border">
            <h2 className="font-semibold text-sm mb-3">Caption Preview</h2>
            <div className="aspect-[9/16] max-w-xs mx-auto bg-gradient-to-b from-violet-900 to-black rounded-xl overflow-hidden relative border border-border">
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-4xl">🎬</span>
              </div>
              <div className={`absolute left-0 right-0 flex flex-wrap justify-center gap-1 px-4 ${
                position === 'top' ? 'top-8' : position === 'center' ? 'top-1/2 -translate-y-1/2' : 'bottom-8'
              }`}>
                {sampleCaptions.map((cap, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 rounded-lg font-bold transition-all"
                    style={{
                      fontSize: `${fontSize * 0.5}px`,
                      color: cap.highlighted ? '#FFD700' : fontColor,
                      textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
                      transform: cap.highlighted ? 'scale(1.1)' : 'scale(1)',
                    }}
                  >
                    {cap.word}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-card border border-border">
            <h2 className="font-semibold text-sm mb-3">Word Timing</h2>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {sampleCaptions.map((cap, i) => (
                <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 text-xs">
                  <span className="w-16 text-muted-foreground">{cap.start.toFixed(2)}s</span>
                  <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-violet-500 rounded-full"
                      style={{ width: `${((cap.end - cap.start) / 2) * 100}%`, marginLeft: `${(cap.start / 2) * 100}%` }}
                    />
                  </div>
                  <span className="w-20 text-right font-medium">{cap.word}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="p-4 rounded-2xl bg-card border border-border">
            <h2 className="font-semibold text-sm mb-3">Presets</h2>
            <div className="grid grid-cols-2 gap-2">
              {captionPresets.map((preset) => (
                <button
                  key={preset.name}
                  onClick={() => setSelectedPreset(preset.name.toLowerCase())}
                  className={`p-3 rounded-xl text-left transition-all ${
                    selectedPreset === preset.name.toLowerCase()
                      ? 'bg-violet-500/10 border border-violet-500/30'
                      : 'bg-muted/50 border border-border hover:border-violet-500/20'
                  }`}
                >
                  <p className="text-xs font-medium">{preset.name}</p>
                  <p className="text-[10px] text-muted-foreground">{preset.font} {preset.size}px</p>
                </button>
              ))}
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-card border border-border space-y-3">
            <h2 className="font-semibold text-sm">Customize</h2>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Font Size</label>
              <input
                type="range"
                min="24"
                max="80"
                value={fontSize}
                onChange={(e) => setFontSize(Number(e.target.value))}
                className="w-full"
              />
              <span className="text-xs text-muted-foreground">{fontSize}px</span>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Font Color</label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={fontColor}
                  onChange={(e) => setFontColor(e.target.value)}
                  className="w-8 h-8 rounded cursor-pointer"
                />
                <span className="text-xs text-muted-foreground">{fontColor}</span>
              </div>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Position</label>
              <select
                value={position}
                onChange={(e) => setPosition(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm"
              >
                <option value="top">Top</option>
                <option value="center">Center</option>
                <option value="bottom">Bottom</option>
              </select>
            </div>
          </div>

          <button className="w-full py-3 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-medium text-sm hover:brightness-110 transition-all">
            Apply Captions
          </button>
        </div>
      </div>
    </div>
  )
}
