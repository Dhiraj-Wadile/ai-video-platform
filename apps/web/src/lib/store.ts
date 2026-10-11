import { create } from 'zustand'

interface User {
  id: string
  email: string
  name: string
  plan?: string
}

interface AppState {
  sidebarOpen: boolean
  toggleSidebar: () => void

  user: User | null
  setUser: (user: User | null) => void

  token: string | null
  setToken: (token: string | null) => void

  currentProject: any | null
  setCurrentProject: (project: any | null) => void

  generatingJob: any | null
  setGeneratingJob: (job: any | null) => void
}

/** The session is restored on reload; without this the dashboard guard bounces signed-in users out. */
function readStoredUser(): User | null {
  if (typeof window === 'undefined') return null
  if (!localStorage.getItem('token')) return null
  try {
    const raw = localStorage.getItem('user')
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    localStorage.removeItem('user')
    return null
  }
}

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  user: readStoredUser(),
  setUser: (user) => {
    if (user) {
      localStorage.setItem('user', JSON.stringify(user))
    } else {
      localStorage.removeItem('user')
    }
    set({ user })
  },

  token: typeof window !== 'undefined' ? localStorage.getItem('token') : null,
  setToken: (token) => {
    if (token) {
      localStorage.setItem('token', token)
    } else {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
    set({ token, user: token ? useAppStore.getState().user : null })
  },

  currentProject: null,
  setCurrentProject: (project) => set({ currentProject: project }),

  generatingJob: null,
  setGeneratingJob: (job) => set({ generatingJob: job }),
}))
