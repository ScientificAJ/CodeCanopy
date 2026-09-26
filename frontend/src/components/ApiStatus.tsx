import type { ApiHealthState } from '../types/api'

interface ApiStatusProps {
  health: ApiHealthState
}

export default function ApiStatus({ health }: ApiStatusProps) {
  const label = {
    loading: 'Checking service',
    connected: 'Connected',
    unavailable: 'Unavailable',
  }[health.status]

  return (
    <section className={`api-status api-status--${health.status}`} aria-live="polite">
      <span className="api-status__indicator" aria-hidden="true" />
      <div>
        <p className="eyebrow">Backend</p>
        <h2>{label}</h2>
        {health.status === 'connected' && <p className="api-status__detail">{health.detail}</p>}
        {health.status === 'unavailable' && <p className="api-status__detail">{health.message}</p>}
      </div>
    </section>
  )
}
