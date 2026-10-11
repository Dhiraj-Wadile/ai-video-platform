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
