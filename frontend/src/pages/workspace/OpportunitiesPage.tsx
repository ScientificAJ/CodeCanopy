// INTEGRATION_SLOT: reuse.findings
// INTEGRATION_SLOT: duplicates.compare
// INTEGRATION_SLOT: unused.review
import { NavLink, useParams } from 'react-router-dom'
import { SlotMount } from '../../components/slots/SlotMount'
import type { SlotId } from '../../contexts/SlotRegistry'
const slots: Record<string, SlotId> = {reuse: 'reuse.findings', duplicates: 'duplicates.compare', unused: 'unused.review'}
export default function OpportunitiesPage() {const {kind = 'reuse'} = useParams(); return <div className="feature-page card"><p className="eyebrow">CODE OPPORTUNITIES</p><div className="tabs">{Object.keys(slots).map(k => <NavLink key={k} to={`../${k}`} relative="path">{k}</NavLink>)}</div><SlotMount id={slots[kind] ?? 'reuse.findings'}/></div>}
