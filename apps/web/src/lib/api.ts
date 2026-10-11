import { formatApiError } from './utils'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const NETWORK_ERROR = `Can't reach the server right now. Please check your connection and try again.`

interface RequestOptions {
  method?: string
  body?: any
  headers?: Record<string, string>
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('token')
}

function handleUnauthorized() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/auth/signin'
  }
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

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, config)
  } catch {
    throw new Error(NETWORK_ERROR)
  }

  if (response.status === 401) {
    handleUnauthorized()
    throw new Error('Your session expired. Please sign in again.')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    const err = new Error(error ? formatApiError(error) : `Request failed (HTTP ${response.status})`)
    // Pages use this to show contextual actions (e.g. an Upgrade link on 402).
    ;(err as any).status = response.status
    throw err
  }

  // 204 / empty bodies (e.g. DELETE) have nothing to parse.
  if (response.status === 204) return undefined as T
  const text = await response.text()
  return (text ? JSON.parse(text) : undefined) as T
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

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, config)
  } catch {
    throw new Error(NETWORK_ERROR)
  }

  if (response.status === 401) {
    handleUnauthorized()
    throw new Error('Your session expired. Please sign in again.')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error ? formatApiError(error) : `Upload failed (HTTP ${response.status})`)
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
  getProjectDetail: (id: string) => request(`/api/projects/${id}/detail`),
  createProject: (data: any) => request('/api/projects', { method: 'POST', body: data }),
  updateProject: (id: string, data: any) => request(`/api/projects/${id}`, { method: 'PATCH', body: data }),
  deleteProject: (id: string) => request(`/api/projects/${id}`, { method: 'DELETE' }),

  updateScene: (projectId: string, sceneId: string, data: any) =>
    request(`/api/projects/${projectId}/scenes/${sceneId}`, { method: 'PATCH', body: data }),
  regenerateScene: (projectId: string, sceneId: string) =>
    request(`/api/projects/${projectId}/scenes/${sceneId}/regenerate`, { method: 'POST' }),

  getProjectQuality: (id: string) => request(`/api/projects/${id}/quality`),
  reviewProjectQuality: (id: string) =>
    request(`/api/projects/${id}/quality/review`, { method: 'POST', body: {} }),
  getProjectCosts: (id: string) => request(`/api/projects/${id}/costs`),
  getProjectLineage: (id: string) => request(`/api/projects/${id}/lineage`),

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
  recut: (projectId: string) => request('/api/render/recut', { method: 'POST', body: { project_id: projectId } }),

  getAnalytics: () => request('/api/analytics'),
  getVideoAnalytics: (projectId: string) => request(`/api/analytics/${projectId}`),

  getCosts: () => request('/api/costs'),
  getProviders: () => request('/api/providers'),

  getPrompts: () => request('/api/prompts'),
  updatePrompt: (id: string, data: any) => request(`/api/prompts/${id}`, { method: 'PATCH', body: data }),

  getPublishingPlatforms: () => request('/api/publishing/platforms'),
  getPublishingJobs: (projectId?: string) =>
    request(`/api/publishing${projectId ? `?project_id=${projectId}` : ''}`),
  schedulePublish: (data: any) => request('/api/publishing/schedule', { method: 'POST', body: data }),
  publishJobNow: (id: string) => request(`/api/publishing/jobs/${id}/publish`, { method: 'POST' }),
  cancelPublishJob: (id: string) => request(`/api/publishing/jobs/${id}/cancel`, { method: 'POST' }),
  deletePublishJob: (id: string) => request(`/api/publishing/jobs/${id}`, { method: 'DELETE' }),

  getMe: () => request('/api/auth/me'),
  getPlans: () => request('/api/billing/plans'),
  getUsage: () => request('/api/billing/usage'),
  billingCheckout: (plan: string, successUrl?: string, cancelUrl?: string) =>
    request('/api/billing/checkout', { method: 'POST', body: { plan, success_url: successUrl, cancel_url: cancelUrl } }),
  billingUpgrade: (plan: string) => request('/api/billing/upgrade', { method: 'POST', body: { plan } }),
}
