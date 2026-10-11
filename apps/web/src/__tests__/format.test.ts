import { describe, it, expect } from 'vitest'
import {
  formatCost,
  formatCostPrecise,
  formatCount,
  formatDate,
  formatDuration,
  formatMs,
} from '@/lib/utils'

describe('formatCost', () => {
  it('converts cents to dollars', () => {
    expect(formatCost(420)).toBe('$4.20')
    expect(formatCost(0)).toBe('$0.00')
  })

  it('treats missing cost as zero', () => {
    expect(formatCost(null)).toBe('$0.00')
    expect(formatCost(undefined)).toBe('$0.00')
  })
})

describe('formatCostPrecise', () => {
  it('keeps three decimals for cheap calls', () => {
    expect(formatCostPrecise(3)).toBe('$0.030')
    expect(formatCostPrecise(null)).toBe('$0.000')
  })
})

describe('formatCount', () => {
  it('abbreviates thousands and millions', () => {
    expect(formatCount(999)).toBe('999')
    expect(formatCount(45_200)).toBe('45.2K')
    expect(formatCount(1_250_000)).toBe('1.3M')
    expect(formatCount(null)).toBe('0')
  })
})

describe('formatMs', () => {
  it('renders latency in seconds', () => {
    expect(formatMs(3400)).toBe('3.4s')
  })

  it('renders a dash when latency is missing', () => {
    expect(formatMs(0)).toBe('—')
    expect(formatMs(null)).toBe('—')
  })
})

describe('formatDuration', () => {
  it('renders m:ss', () => {
    expect(formatDuration(23)).toBe('0:23')
    expect(formatDuration(75)).toBe('1:15')
  })
})

describe('formatDate', () => {
  it('formats an ISO timestamp', () => {
    expect(formatDate('2026-09-25T10:30:00Z')).toMatch(/Sep/)
  })
})
