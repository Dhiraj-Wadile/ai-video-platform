import { Users, Plus, Edit2, Trash2 } from 'lucide-react'
import Link from 'next/link'

const characters = [
  {
    id: '1',
    name: 'Professor AI',
    appearance: 'Wearing glasses, lab coat, friendly face',
    personality: 'Curious, educational, enthusiastic',
    catchphrases: ['Let me blow your mind!', 'Did you know?'],
    videosCount: 12,
  },
  {
    id: '2',
    name: 'Money Master',
    appearance: 'Business suit, confident posture, warm smile',
    personality: 'Wise, practical, motivational',
    catchphrases: ['Money talks, are you listening?', 'Invest in yourself first'],
    videosCount: 8,
  },
  {
    id: '3',
    name: 'Tech Whisperer',
    appearance: 'Casual hoodie, futuristic glasses, young',
    personality: 'Innovative, excited, relatable',
    catchphrases: ['The future is now!', 'Code your destiny'],
    videosCount: 15,
  },
]

export default function CharactersPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Users className="w-6 h-6 text-violet-500" />
            Characters
          </h1>
          <p className="text-sm text-muted-foreground">Create and manage your original video characters</p>
        </div>
        <Link
          href="/create/characters/new"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500/10 text-violet-500 font-medium hover:bg-violet-500/20 transition-colors text-sm"
        >
          <Plus className="w-4 h-4" /> New Character
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {characters.map((char) => (
          <div key={char.id} className="p-5 rounded-2xl bg-card border border-border hover:border-violet-500/30 transition-colors">
            <div className="flex items-start justify-between mb-3">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-violet-500/20 to-purple-500/10 flex items-center justify-center text-2xl">
                👤
              </div>
              <div className="flex items-center gap-1">
                <button className="p-1.5 rounded-lg hover:bg-accent transition-colors">
                  <Edit2 className="w-4 h-4 text-muted-foreground" />
                </button>
                <button className="p-1.5 rounded-lg hover:bg-red-500/10 transition-colors">
                  <Trash2 className="w-4 h-4 text-muted-foreground hover:text-red-500" />
                </button>
              </div>
            </div>
            <h3 className="font-semibold mb-1">{char.name}</h3>
            <p className="text-xs text-muted-foreground mb-2">{char.appearance}</p>
            <p className="text-xs text-muted-foreground mb-3">{char.personality}</p>
            <div className="flex flex-wrap gap-1 mb-3">
              {char.catchphrases.map((cp) => (
                <span key={cp} className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-500">
                  &ldquo;{cp}&rdquo;
                </span>
              ))}
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground pt-3 border-t border-border">
              <span>{char.videosCount} videos</span>
              <Link href={`/create/characters/${char.id}`} className="text-violet-500 hover:underline">
                View details
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
