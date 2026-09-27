import { useState } from 'react'
import { SlotMount } from '../../components/slots/SlotMount'

export default function ProposalsPage() {
  const [mode, setMode] = useState<'draft' | 'derived'>('draft')
  return <div className="feature-page card">
    <p className="eyebrow">PLAN YOUR NEXT CHANGE</p>
    <div className="source-switch" role="group" aria-label="Proposal view">
      <button type="button" aria-pressed={mode === 'draft'} onClick={() => setMode('draft')}>AI-assisted plan</button>
      <button type="button" aria-pressed={mode === 'derived'} onClick={() => setMode('derived')}>Source-derived suggestions</button>
    </div>
    <SlotMount id={mode === 'draft' ? 'proposals.detail' : 'proposals.derived'}/>
  </div>
}
