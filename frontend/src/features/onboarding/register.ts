import { registerFeature } from '../../contexts/FeatureContracts'
import { ProposalsPanel } from './ProposalsPanel'
import { request, snapshotPath } from '../../services/v1/api'
import type { ChangePack } from '../../types/v1/prd.generated'

registerFeature('proposals.derived', {
  Component: ProposalsPanel,
  load: (context, signal) => {
    const base = snapshotPath(context.projectId, context.snapshotId) + '/proposals'
    const path = context.selectedEntity?.path
    const url = path && path !== '.' ? `${base}?subject=${encodeURIComponent(path)}` : base
    return request<ChangePack>(url, { signal })
  },
})
