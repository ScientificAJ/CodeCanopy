import { registerSlot, type SlotProps } from '../../contexts/SlotRegistry'
import { DraftWorkspace } from './DraftWorkspace'
function Proposals(props: SlotProps) {return <DraftWorkspace {...props} kind="proposal"/>}
function Documentation(props: SlotProps) {return <DraftWorkspace {...props} kind="documentation"/>}
registerSlot('proposals.detail', Proposals)
registerSlot('docs.generated', Documentation)
