import { describe, it, expect } from 'vitest'
import {
  formatCost,
  formatCostPrecise,
  formatCount,
  formatDate,
  formatDuration,
  formatMs,
  formatApiError,
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

describe('formatApiError', () => {
  it('returns a plain string detail as-is', () => {
    expect(formatApiError({ detail: 'Invalid credentials' })).toBe('Invalid credentials')
  })

  it('reads a bare string', () => {
    expect(formatApiError('Something broke')).toBe('Something broke')
  })

  it('turns FastAPI validation errors into readable text', () => {
    const error = {
      detail: [{ loc: ['body', 'project_id'], msg: 'Field required', type: 'missing' }],
    }
    expect(formatApiError(error)).toBe('project id Field required')
  })

  it('joins multiple validation errors', () => {
    const error = {
      detail: [
        { loc: ['body', 'email'], msg: 'invalid email' },
        { loc: ['body', 'password'], msg: 'too short' },
      ],
    }
    expect(formatApiError(error)).toBe('email invalid email, password too short')
  })

  it('never renders "[object Object]"', () => {
    const result = formatApiError({ detail: { weird: true } })
    expect(result).not.toContain('[object Object]')
    expect(result.length).toBeGreaterThan(0)
  })

  it('handles null and undefined', () => {
    expect(formatApiError(null)).toMatch(/try again/i)
    expect(formatApiError(undefined)).toMatch(/try again/i)
  })
})
