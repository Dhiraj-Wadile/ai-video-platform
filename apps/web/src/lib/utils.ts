import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

export function formatCost(cents: number | null | undefined): string {
  return `$${((cents || 0) / 100).toFixed(2)}`
}

export function formatCostPrecise(cents: number | null | undefined): string {
  return `$${((cents || 0) / 100).toFixed(3)}`
}

export function formatMs(ms: number | null | undefined): string {
  if (!ms) return '—'
  return `${(ms / 1000).toFixed(1)}s`
}

export function formatCount(n: number | null | undefined): string {
  const value = n || 0
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return String(value)
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

/**
 * Turns anything the API can hand back into a sentence a non-technical user can act on.
 * FastAPI validation errors arrive as `{ detail: [{ loc, msg, type }] }`, which used to be
 * rendered as "[object Object]" by the old `new Error(error.detail)` call.
 */
export function formatApiError(input: unknown): string {
  if (input == null) return 'Something went wrong. Please try again.'

  const detail =
    typeof input === 'object' && input !== null && 'detail' in input
      ? (input as { detail: unknown }).detail
      : input

  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object') {
          const obj = item as { loc?: unknown; msg?: unknown }
          const field = Array.isArray(obj.loc) ? obj.loc[obj.loc.length - 1] : undefined
          const msg = typeof obj.msg === 'string' ? obj.msg : 'is invalid'
          return field ? `${String(field).replace(/_/g, ' ')} ${msg}` : msg
        }
        return null
      })
      .filter((m): m is string => Boolean(m))
    return messages.join(', ') || 'Please check your input and try again.'
  }

  if (detail && typeof detail === 'object' && 'msg' in detail) {
    const msg = (detail as { msg: unknown }).msg
    if (typeof msg === 'string') return msg
  }

  return 'Something went wrong. Please try again.'
}

/** localStorage flag set once a user completes or skips the onboarding wizard. */
export const ONBOARDING_KEY = 'onboarding_done'

/** Ready-made prompts so a first-time user never faces a blank box. */
export const VIDEO_IDEAS: string[] = [
  '5 habits that make you successful',
  'Why AI is changing everything',
  'A 60-second history of the internet',
  '3 money mistakes to avoid in your 20s',
  'How to learn anything twice as fast',
  'The science of a perfect morning routine',
  'Hidden features in your phone you never use',
  'What happens to your brain when you scroll',
]
