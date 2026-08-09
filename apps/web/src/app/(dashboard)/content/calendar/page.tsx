'use client'

import { useState } from 'react'
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Plus } from 'lucide-react'

const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

const scheduledVideos = [
  { date: '2026-08-10', title: 'AI Habits Video', status: 'scheduled', time: '10:00 AM' },
  { date: '2026-08-12', title: 'Money Tips Part 2', status: 'draft', time: '2:00 PM' },
  { date: '2026-08-15', title: 'Startup Story', status: 'scheduled', time: '6:00 PM' },
]

export default function CalendarPage() {
  const [currentMonth, setCurrentMonth] = useState(7) // August (0-indexed)
  const [currentYear] = useState(2026)

  const firstDay = new Date(currentYear, currentMonth, 1).getDay()
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate()

  const cells = []
  for (let i = 0; i < firstDay; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <CalendarIcon className="w-6 h-6 text-violet-500" />
            Content Calendar
          </h1>
          <p className="text-sm text-muted-foreground">Schedule and manage your publishing pipeline</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500/10 text-violet-500 font-medium hover:bg-violet-500/20 transition-colors text-sm">
          <Plus className="w-4 h-4" /> Schedule Video
        </button>
      </div>

      <div className="p-4 rounded-2xl bg-card border border-border">
        <div className="flex items-center justify-between mb-4">
          <button onClick={() => setCurrentMonth(Math.max(0, currentMonth - 1))} className="p-1.5 rounded hover:bg-accent"><ChevronLeft className="w-5 h-5" /></button>
          <h2 className="font-semibold">{months[currentMonth]} {currentYear}</h2>
          <button onClick={() => setCurrentMonth(Math.min(11, currentMonth + 1))} className="p-1.5 rounded hover:bg-accent"><ChevronRight className="w-5 h-5" /></button>
        </div>

        <div className="grid grid-cols-7 gap-px bg-border rounded-xl overflow-hidden">
          {days.map((day) => (
            <div key={day} className="bg-muted p-2 text-center text-xs font-medium text-muted-foreground">
              {day}
            </div>
          ))}
          {cells.map((day, i) => {
            const dateStr = day ? `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}` : ''
            const events = scheduledVideos.filter(v => v.date === dateStr)
            return (
              <div key={i} className={`bg-card p-2 min-h-[80px] ${day ? 'hover:bg-muted/50' : ''} transition-colors`}>
                {day && (
                  <>
                    <span className="text-xs text-muted-foreground">{day}</span>
                    {events.map((event, j) => (
                      <div key={j} className={`mt-1 text-[10px] px-1.5 py-0.5 rounded ${
                        event.status === 'scheduled' ? 'bg-violet-500/10 text-violet-500' : 'bg-muted text-muted-foreground'
                      }`}>
                        {event.title}
                      </div>
                    ))}
                  </>
                )}
              </div>
            )
          })}
        </div>
      </div>

      <div className="p-4 rounded-2xl bg-card border border-border">
        <h2 className="font-semibold text-sm mb-3">Upcoming</h2>
        <div className="space-y-2">
          {scheduledVideos.map((video, i) => (
            <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-muted/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-violet-500/10 flex items-center justify-center text-sm font-bold">
                  {new Date(video.date).getDate()}
                </div>
                <div>
                  <p className="text-sm font-medium">{video.title}</p>
                  <p className="text-xs text-muted-foreground">{video.time}</p>
                </div>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                video.status === 'scheduled' ? 'bg-violet-500/10 text-violet-500' : 'bg-muted text-muted-foreground'
              }`}>
                {video.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
