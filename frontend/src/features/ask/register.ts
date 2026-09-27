import { registerFeature } from '../../contexts/FeatureContracts'
import CodeChat from './CodeChat'
import { request, snapshotPath } from '../../services/v1/api'
import type { Answer } from '../../types/v1/prd.generated'

// The GET /ask slot endpoint returns AskResponse {answer: string, context_hint: string}.
// CodeChat reads request.data.answer to display the greeting before the first
// conversation message. The cast to Answer satisfies the FeatureContracts generic
// boundary without altering the shared contract.
registerFeature('ask.workspace', {
  Component: CodeChat as Parameters<typeof registerFeature<'ask.workspace'>>[1]['Component'],
  load: (context, signal) => {
    const url = snapshotPath(context.projectId, context.snapshotId) + '/ask'
    return request<{ answer: string; context_hint: string }>(url, { signal }) as unknown as Promise<Answer>
  },
})
