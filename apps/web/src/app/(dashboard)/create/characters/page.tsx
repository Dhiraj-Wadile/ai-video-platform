'use client'

import { useEffect, useState } from 'react'
import { Users, Plus, Loader2, AlertCircle, Sparkles, X } from 'lucide-react'
import { api } from '@/lib/api'

interface Character {
  id: string
  name: string
  appearance: string | null
  personality: string | null
  speaking_style: string | null
  catchphrases: string[] | null
  background: string | null
}

const EMPTY_FORM = { name: '', description: '', character_type: 'general' }

export default function CharactersPage() {
  const [characters, setCharacters] = useState<Character[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState<Partial<Character>>({})
  const [savingId, setSavingId] = useState<string | null>(null)

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const data: any = await api.getCharacters()
      setCharacters(Array.isArray(data) ? data : [])
    } catch (err: any) {
      setError(err.message || 'Could not load characters')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate() {
    if (!form.name.trim()) return
    setCreating(true)
    setError('')
    try {
      const created: any = await api.createCharacter(form)
      setCharacters((prev) => [created, ...prev])
      setForm(EMPTY_FORM)
      setShowForm(false)
    } catch (err: any) {
      setError(err.message || 'Could not create character')
    } finally {
      setCreating(false)
    }
  }

  async function handleSave(id: string) {
    setSavingId(id)
    setError('')
    try {
      const updated: any = await api.updateCharacter(id, {
        name: draft.name,
        appearance: draft.appearance,
        personality: draft.personality,
        speaking_style: draft.speaking_style,
        catchphrases: draft.catchphrases,
        background: draft.background,
      })
      setCharacters((prev) => prev.map((c) => (c.id === id ? { ...c, ...updated } : c)))
      setEditingId(null)
      setDraft({})
    } catch (err: any) {
      setError(err.message || 'Could not save character')
    } finally {
      setSavingId(null)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Users className="w-6 h-6 text-violet-500" />
            Characters
          </h1>
          <p className="text-sm text-muted-foreground">
            Reusable personas keep look and voice consistent across videos
          </p>
        </div>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500/10 text-violet-500 font-medium hover:bg-violet-500/20 transition-colors text-sm"
        >
          {showForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          {showForm ? 'Cancel' : 'New Character'}
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-destructive/10 text-destructive text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      )}

      {showForm && (
        <div className="p-4 rounded-2xl bg-card border border-border space-y-3">
          <h2 className="font-semibold text-sm">Create a character</h2>
          <p className="text-xs text-muted-foreground">
            The character agent writes the appearance, personality and voice so the same persona can be reused.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Name"
              className="px-3 py-2 rounded-lg bg-background border border-border text-sm"
            />
            <select
              value={form.character_type}
              onChange={(e) => setForm({ ...form, character_type: e.target.value })}
              className="px-3 py-2 rounded-lg bg-background border border-border text-sm"
            >
              <option value="general">General</option>
              <option value="host">Host / Presenter</option>
              <option value="expert">Expert</option>
              <option value="narrator">Narrator</option>
              <option value="character">Fictional character</option>
            </select>
            <input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Who are they? (optional)"
              className="px-3 py-2 rounded-lg bg-background border border-border text-sm"
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={creating || !form.name.trim()}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500 text-white text-sm font-medium hover:brightness-110 disabled:opacity-50"
          >
            {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            Generate character
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : characters.length === 0 ? (
        <div className="p-12 rounded-2xl bg-card border border-border text-center">
          <Users className="w-12 h-12 mx-auto text-muted-foreground mb-3 opacity-50" />
          <p className="text-muted-foreground">No characters yet</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {characters.map((char) => (
            <div key={char.id} className="p-5 rounded-2xl bg-card border border-border space-y-2">
              {editingId === char.id ? (
                <div className="space-y-2">
                  {(['name', 'appearance', 'personality', 'speaking_style'] as const).map((field) => (
                    <input
                      key={field}
                      value={(draft[field] as string) ?? char[field] ?? ''}
                      onChange={(e) => setDraft({ ...draft, [field]: e.target.value })}
                      placeholder={field.replace('_', ' ')}
                      className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm"
                    />
                  ))}
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleSave(char.id)}
                      disabled={savingId === char.id}
                      className="flex-1 px-3 py-2 rounded-lg bg-violet-500 text-white text-xs font-medium disabled:opacity-50"
                    >
                      {savingId === char.id ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={() => { setEditingId(null); setDraft({}) }}
                      className="px-3 py-2 rounded-lg border border-border text-xs"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold">{char.name}</h3>
                    <button
                      onClick={() => { setEditingId(char.id); setDraft({}) }}
                      className="text-[10px] text-muted-foreground hover:text-violet-500 shrink-0"
                    >
                      Edit
                    </button>
                  </div>
                  {char.appearance && <p className="text-xs text-muted-foreground">{char.appearance}</p>}
                  {char.personality && <p className="text-xs text-muted-foreground">{char.personality}</p>}
                  {char.catchphrases && char.catchphrases.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {char.catchphrases.map((cp, i) => (
                        <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-500">
                          {cp}
                        </span>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
