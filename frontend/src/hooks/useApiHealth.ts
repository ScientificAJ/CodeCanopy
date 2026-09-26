import { useEffect, useState } from 'react'
import { getHealth } from '../services/api'
import type { ApiHealthState } from '../types/api'

export function useApiHealth(): ApiHealthState {
  const [health, setHealth] = useState<ApiHealthState>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()

    getHealth(controller.signal)
      .then((response) => {
        setHealth({ status: 'connected', detail: response.status })
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const message = error instanceof Error ? error.message : 'Unable to reach the API'
        setHealth({ status: 'unavailable', message })
      })

    return () => controller.abort()
  }, [])

  return health
}
