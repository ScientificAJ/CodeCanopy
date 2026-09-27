import { registerFeature } from '../../contexts/FeatureContracts'
import { SummaryPanel } from './SummaryPanel'
import { request, snapshotPath } from '../../services/v1/api'
import type { SummaryPayload } from '../../contexts/FeatureContracts'

registerFeature('summaries.context-panel', {
  Component: SummaryPanel,
  loadKey: context => context.selectedEntity?.path || '.',
  load: (context, signal) => {
    const base = snapshotPath(context.projectId, context.snapshotId) + '/summaries'
    const path = context.selectedEntity?.path
    const url = path && path !== '.' ? `${base}?path=${encodeURIComponent(path)}` : base
    return request<SummaryPayload>(url, { signal })
  },
})
