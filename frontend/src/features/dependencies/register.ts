import { registerFeature } from '../../contexts/FeatureContracts'
import { DependencyPanel } from './DependencyPanel'
import { request, snapshotPath } from '../../services/v1/api'
import type { DependencyOverlay } from '../../contexts/FeatureContracts'

registerFeature('dependencies.workspace', {
  Component: DependencyPanel,
  load: (context, signal) => {
    const base = snapshotPath(context.projectId, context.snapshotId) + '/dependencies'
    const path = context.selectedEntity?.path
    const url = path && path !== '.' ? `${base}?path=${encodeURIComponent(path)}` : base
    return request<DependencyOverlay>(url, { signal })
  },
})
