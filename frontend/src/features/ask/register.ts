import { registerFeature } from '../../contexts/FeatureContracts'
import CodeChat from './CodeChat'
import { request, snapshotPath } from '../../services/v1/api'
import type { AskResponse } from '../../types/v1/chat'

registerFeature('ask.workspace', {
  Component: CodeChat,
  load: (context, signal) => request<AskResponse>(
    snapshotPath(context.projectId, context.snapshotId) + '/ask', { signal },
  ),
})
