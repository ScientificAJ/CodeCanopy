// INTEGRATION_SLOT: reuse.findings
// INTEGRATION_SLOT: duplicates.compare
// INTEGRATION_SLOT: unused.review
import { NavLink, useParams } from 'react-router-dom'
import { SlotMount } from '../../components/slots/SlotMount'
import type { SlotId } from '../../contexts/SlotRegistry'
const views: {id: string; label: string; slot: SlotId}[] = [
	{id: 'reuse', label: 'Reusable code', slot: 'reuse.findings'},
	{id: 'duplicates', label: 'Duplicates', slot: 'duplicates.compare'},
	{id: 'unused', label: 'Potentially unused', slot: 'unused.review'},
]
export default function OpportunitiesPage() {
	const {kind = 'reuse'} = useParams()
	const active = views.find(view => view.id === kind) ?? views[0]
	return <div className="feature-page card"><p className="eyebrow">CODE OPPORTUNITIES</p><div className="tabs">{views.map(view => <NavLink key={view.id} to={`../${view.id}`} relative="path">{view.label}</NavLink>)}</div><SlotMount id={active.slot}/></div>
}
