import { registerFeature } from '../../contexts/FeatureContracts'
import { ReusableFunctionPanel } from './ReusableFunctionPanel'
import { getReusableFunctions } from '../../services/v1/api'

registerFeature('reuse.findings', {
  Component: ReusableFunctionPanel as never,
  load: (context, signal) => getReusableFunctions(context.projectId, context.snapshotId, 1, signal) as never,
})
