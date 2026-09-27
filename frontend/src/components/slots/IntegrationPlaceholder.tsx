/**
 * IntegrationPlaceholder — renders an intentional "not connected" state
 * for deferred feature modules.
 *
 * This is used for all six teammate-owned features:
 *   - AI Summaries
 *   - Dependencies / Change Impact
 *   - Reuse / Duplicates / Unused (Opportunities)
 *   - Ask Grepo
 *   - Proposals & Change Packs
 *
 * The placeholder is:
 *   - Visually intentional (dashed border, explicit badge)
 *   - Accessible (proper heading, descriptive text)
 *   - Developer-informative (shows slot path, contract, registration steps)
 *   - Never presenting fictional success results
 */

import type { SlotId } from '../../contexts/SlotRegistry'

interface Props {
  slotId: SlotId
  title: string
  description: string
  integrationPath?: string
  /** Show the developer disclosure panel (default: false in user-facing view) */
  showDevDisclosure?: boolean
  /** Optional back action (e.g., "Back to map") */
  onBack?: () => void
  backLabel?: string
}

export function IntegrationPlaceholder({
  slotId,
  title,
  description,
  integrationPath,
  showDevDisclosure = false,
  onBack,
  backLabel = 'Back to Map',
}: Props) {
  return (
    <div className="slot-placeholder" role="region" aria-label={`${title} — integration slot`}>
      <span className="slot-placeholder__badge" aria-hidden="true">Integration Slot</span>

      <h2 className="slot-placeholder__title">{title}</h2>
      <p className="slot-placeholder__description">{description}</p>

      {onBack && (
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={onBack}
        >
          ← {backLabel}
        </button>
      )}

      {showDevDisclosure && (
        <div className="slot-placeholder__dev" aria-label="Developer integration details">
          <p className="slot-placeholder__dev-title">Developer integration details</p>
          <code className="slot-placeholder__code">
{`Slot ID:       ${slotId}
Module path:   ${integrationPath ?? '(not set)'}

Registration:
  import { registerSlot } from 'src/contexts/SlotRegistry'
  import { MyFeatureComponent } from './${slotId.split('.')[0]}'
  registerSlot('${slotId}', MyFeatureComponent)

Input contract: SlotProps (src/contexts/SlotRegistry.ts)
  - projectId: string
  - snapshotId: string
  - snapshot: Snapshot
  - selectedEntity: SelectedEntity | null
  - files: FileRecord[]

See INTEGRATION_GUIDE.md for full registration steps.`}
          </code>
        </div>
      )}
    </div>
  )
}
