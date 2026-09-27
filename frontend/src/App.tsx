/**
 * Grepo application root — sets up routing and the app shell.
 *
 * Route structure (PRD §7.1):
 *   /                                       — Import page
 *   /p/:projectId                           — Project root (redirects to latest snapshot)
 *   /p/:projectId/s/:snapshotId/overview    — Repository overview
 *   /p/:projectId/s/:snapshotId/map         — Structure map
 *   /p/:projectId/s/:snapshotId/dependencies — Dependencies (integration slot)
 *   /p/:projectId/s/:snapshotId/opportunities/:kind — Opportunities (integration slot)
 *   /p/:projectId/s/:snapshotId/ask         — Ask Grepo (integration slot)
 *   /p/:projectId/s/:snapshotId/proposals   — Proposals (integration slot)
 */

import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import ImportPage from './pages/ImportPage'
import { ProjectRoot, WorkspaceLayout } from './pages/workspace/WorkspaceLayout'
import OverviewPage from './pages/workspace/OverviewPage'
import MapPage from './pages/workspace/MapPage'
import DependenciesPage from './pages/workspace/DependenciesPage'
import OpportunitiesPage from './pages/workspace/OpportunitiesPage'
import AskPage from './pages/workspace/AskPage'
import { SlotMount } from './components/slots/SlotMount'
import ProposalsPage from './pages/workspace/ProposalsPage'
import './features/duplicate_detection'
import './styles.css'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Import landing page */}
        <Route path="/" element={<ImportPage />} />

        {/* Project root — redirects to latest snapshot */}
        <Route path="/p/:projectId" element={<ProjectRoot />} />

        {/* Workspace — all routes under a snapshot */}
        <Route path="/p/:projectId/s/:snapshotId" element={<WorkspaceLayout />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<OverviewPage />} />
          <Route path="map" element={<MapPage />} />
          <Route path="dependencies" element={<DependenciesPage />} />
          <Route path="opportunities" element={<Navigate to="reuse" replace />} />
          <Route path="opportunities/:kind" element={<OpportunitiesPage />} />
          <Route path="ask" element={<AskPage />} />
          <Route path="docs" element={<div className="feature-page card"><SlotMount id="docs.generated"/></div>} />
          <Route path="proposals" element={<ProposalsPage />} />
          <Route path="proposals/:proposalId" element={<ProposalsPage />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
