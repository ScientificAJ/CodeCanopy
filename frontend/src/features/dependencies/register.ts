import { registerFeature } from '../../contexts/FeatureContracts'
import { DependencyExplorer } from './DependencyExplorer'
import { request, snapshotPath } from '../../services/v1/api'
import type { DependencyResult } from './types'

registerFeature('dependencies.workspace', {
  Component: DependencyExplorer,
  loadKey: () => 'snapshot',
  load: (context, signal) => request<DependencyResult>(
    snapshotPath(context.projectId, context.snapshotId) + '/dependencies', { signal },
  ),
})
