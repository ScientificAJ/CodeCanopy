import { registerFeature } from '../../contexts/FeatureContracts'
import { request, snapshotPath } from '../../services/v1/api'
import { DependencyExplorer } from './DependencyExplorer'
import type { DependencyResult } from './types'
registerFeature('dependencies.workspace', {
  Component: DependencyExplorer,
  load: (context, signal) => request<DependencyResult>(snapshotPath(context.projectId, context.snapshotId) + '/dependencies', {signal}),
})
