import { useEffect, useState } from 'react'
import type { AnalysisRun } from '../types/v1'
import './ImportLoader.css'

const notes = [
  'Tiny gecko. Big repository.',
  'Following the branches. Leaving the bugs alone.',
  'No code is running. Just a very curious gecko.',
  'Every great code adventure starts with a map.',
]

export function ImportLoader({ run, source, onCancel }: {
  run: AnalysisRun | null
  source: 'github' | 'zip'
  onCancel?: () => void
}) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const start = Date.now()
    const timer = setInterval(() => setSeconds(Math.floor((Date.now() - start) / 1000)), 1000)
    return () => clearInterval(timer)
  }, [])
  const indexing = run?.stage === 'inventory' || run?.stage === 'parse'
  const stage = !run ? 0 : indexing ? 2 : 1
  const progress = indexing && typeof run?.stage_progress === 'number' ? Math.round(run.stage_progress * 100) : null
  const label = !run ? source === 'zip' ? 'Uploading your archive' : 'Connecting to GitHub'
    : run.status === 'queued' ? 'Your expedition is queued'
      : indexing ? 'Reading files & tracing the code' : source === 'github' ? 'Fetching & unpacking your repository' : 'Unpacking your repository'
  return <section className="gecko-loader" aria-label="Repository import progress">
    <div className="gecko-loader-top"><span><i aria-hidden="true"/> EXPEDITION IN PROGRESS</span><span aria-label={`${seconds} seconds elapsed`}>{Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}</span></div>
    <div className="gecko-trail" aria-hidden="true">
      <span className="trail-file trail-file-one">{'{ }'}</span><span className="trail-file trail-file-two">&lt;/&gt;</span><span className="trail-file trail-file-three">#</span>
      <div className="gecko-scout"><img src="/codecanopy-logo.png" alt=""/></div>
      <div className="trail-ground"/><span className="trail-spark spark-one">✦</span><span className="trail-spark spark-two">✦</span>
    </div>
    <div role="status" aria-live="polite" aria-atomic="true"><h2>{label}</h2></div>
    <p className="gecko-loader-note" aria-hidden="true">{notes[Math.floor(seconds / 7) % notes.length]}</p>
    {progress === null ? <div className="gecko-track indeterminate" role="progressbar" aria-label={label}><span/></div>
      : <><div className="gecko-progress-label"><span>Files inspected</span><strong>{progress}%</strong></div><div className="gecko-track" role="progressbar" aria-label="Files inspected" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><span style={{width:`${progress}%`}}/></div></>}
    <ol className="gecko-stages" aria-label="Import stages">{['Collect', 'Unpack', 'Explore'].map((name, i) => <li key={name} className={i < stage ? 'done' : i === stage ? 'active' : ''} aria-current={i === stage ? 'step' : undefined}><span aria-hidden="true">{i < stage ? '✓' : `0${i + 1}`}</span>{name}</li>)}</ol>
    <div className="gecko-loader-footer"><small>Your source stays read-only.</small>{onCancel && <button type="button" onClick={onCancel}>Cancel import</button>}</div>
  </section>
}
