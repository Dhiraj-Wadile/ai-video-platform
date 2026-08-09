import { create } from 'zustand'

interface User {
  id: string
  email: string
  name: string
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

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  user: null,
  setUser: (user) => set({ user }),

  token: typeof window !== 'undefined' ? localStorage.getItem('token') : null,
  setToken: (token) => {
    if (token) {
      localStorage.setItem('token', token)
    } else {
      localStorage.removeItem('token')
    }
    set({ token })
  },

  currentProject: null,
  setCurrentProject: (project) => set({ currentProject: project }),

  generatingJob: null,
  setGeneratingJob: (job) => set({ generatingJob: job }),
}))
