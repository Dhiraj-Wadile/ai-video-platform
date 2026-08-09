const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface RequestOptions {
  method?: string
  body?: any
  headers?: Record<string, string>
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('token')
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = options

  const token = getToken()
  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  }

  if (token) {
    ;(config.headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
  }

  if (body) {
    config.body = JSON.stringify(body)
  }

  const response = await fetch(`${API_BASE}${path}`, config)

  if (response.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token')
      window.location.href = '/auth/signin'
    }
    throw new Error('Unauthorized')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

async function uploadFile<T>(path: string, file: File, extraData?: Record<string, string>): Promise<T> {
  const token = getToken()
  const formData = new FormData()
  formData.append('file', file)
  if (extraData) {
    Object.entries(extraData).forEach(([k, v]) => formData.append(k, v))
  }

  const config: RequestInit = {
    method: 'POST',
    body: formData,
  }

  if (token) {
    config.headers = { Authorization: `Bearer ${token}` }
  }

  const response = await fetch(`${API_BASE}${path}`, config)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

export const api = {
  login: (email: string, password: string) =>
    request('/api/auth/login', { method: 'POST', body: { email, password } }),
  register: (email: string, password: string, name: string) =>
    request('/api/auth/register', { method: 'POST', body: { email, password, name } }),

  getProjects: () => request('/api/projects'),
  getProject: (id: string) => request(`/api/projects/${id}`),
  createProject: (data: any) => request('/api/projects', { method: 'POST', body: data }),
  updateProject: (id: string, data: any) => request(`/api/projects/${id}`, { method: 'PATCH', body: data }),
  deleteProject: (id: string) => request(`/api/projects/${id}`, { method: 'DELETE' }),

  generateScript: (data: any) => request('/api/scripts/generate', { method: 'POST', body: data }),
  getScript: (id: string) => request(`/api/scripts/${id}`),

  getCharacters: () => request('/api/characters'),
  createCharacter: (data: any) => request('/api/characters', { method: 'POST', body: data }),
  updateCharacter: (id: string, data: any) => request(`/api/characters/${id}`, { method: 'PATCH', body: data }),

  generateStoryboard: (data: any) => request('/api/storyboard/generate', { method: 'POST', body: data }),

  uploadAsset: (file: File, assetType: string, projectId?: string) =>
    uploadFile('/api/assets/upload', file, { asset_type: assetType, project_id: projectId || '' }),

  getAgents: () => request('/api/agents'),
  runAgent: (name: string, input: any) => request(`/api/agents/${name}/run`, { method: 'POST', body: input }),
  getAgentRuns: () => request('/api/agents/runs'),

  getTrends: () => request('/api/trends'),
  analyzeTrend: (topic: string) => request('/api/trends/analyze', { method: 'POST', body: { topic } }),

  startRender: (data: any) => request('/api/render/start', { method: 'POST', body: data }),
  getRenderStatus: (jobId: string) => request(`/api/render/status/${jobId}`),

  getAnalytics: () => request('/api/analytics'),
  getVideoAnalytics: (projectId: string) => request(`/api/analytics/${projectId}`),

  getPrompts: () => request('/api/prompts'),
  updatePrompt: (id: string, data: any) => request(`/api/prompts/${id}`, { method: 'PATCH', body: data }),
}
