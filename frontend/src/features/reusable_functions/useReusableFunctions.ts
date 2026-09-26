import { useEffect, useState } from 'react'
import { getReusableFunctions } from '../../services/v1/api'
import type { ReusableFunctionResult } from '../../types/codebase'

export function useReusableFunctions(projectId: string, snapshotId: string) {
  const [data, setData] = useState<ReusableFunctionResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(''); setData(null)
    getReusableFunctions(projectId, snapshotId, 1, controller.signal)
      .then(setData)
      .catch(e => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Failed to load.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [projectId, snapshotId])

  return { data, loading, error }
}
