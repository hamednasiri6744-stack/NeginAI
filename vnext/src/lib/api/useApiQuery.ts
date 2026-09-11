import { useQuery } from '@tanstack/react-query'
import { queryClient } from '../query/client'

export function clearApiQueryCache() {
  queryClient.clear()
}

export function useApiQuery<T>(
  key: string,
  queryFn: (signal: AbortSignal) => Promise<T>,
  staleMs = 30_000,
) {
  const query = useQuery({
    queryKey: [key],
    queryFn: ({ signal }) => queryFn(signal),
    staleTime: staleMs,
  })

  const status = query.status === 'pending' ? 'loading' : query.status === 'error' ? 'error' : 'success'

  return {
    data: query.data ?? null,
    status,
    error: query.error instanceof Error ? query.error : null,
    reload: () => { void queryClient.invalidateQueries({ queryKey: [key] }) },
  } as const
}
