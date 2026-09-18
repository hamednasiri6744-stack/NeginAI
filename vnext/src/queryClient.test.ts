// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { queryClient } from './queryClient'

describe('queryClient', () => {
  it('uses bounded cache defaults for NeginAI server state', () => {
    const defaults = queryClient.getDefaultOptions()
    expect(defaults.queries?.staleTime).toBe(30_000)
    expect(defaults.queries?.gcTime).toBe(300_000)
    expect(defaults.queries?.retry).toBe(1)
    expect(defaults.mutations?.retry).toBe(0)
  })
})
