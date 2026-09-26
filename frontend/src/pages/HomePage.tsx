import { useState } from 'react'
import ApiStatus from '../components/ApiStatus'
import ProjectTree from '../components/ProjectTree'
import ProjectUpload from '../components/ProjectUpload'
import { useApiHealth } from '../hooks/useApiHealth'
import { analyzeProject, getProject } from '../services/api'
import type { File as ProjectFile, Project } from '../types/codebase'
import type { ProjectUploadResponse } from '../types/api'

function formatSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unable to load this project.'
}

export default function HomePage() {
  const health = useApiHealth()
  const [project, setProject] = useState<Project | null>(null)
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null)
  const [isLoadingProject, setIsLoadingProject] = useState(false)
  const [analysisComplete, setAnalysisComplete] = useState(false)
  const [projectError, setProjectError] = useState<string | null>(null)
  const selectedFile = project?.files.find((file) => file.path === selectedFilePath) ?? null

  async function handleUploaded(uploadedProject: ProjectUploadResponse): Promise<void> {
    setProject(null)
    setSelectedFilePath(null)
    setAnalysisComplete(false)
    setProjectError(null)
    setIsLoadingProject(true)
    try {
      const loadedProject = await getProject(uploadedProject.project_id)
      setProject(loadedProject)
      try {
        const analyzedFiles = await analyzeProject(uploadedProject.project_id)
        const resultsByPath = new Map(analyzedFiles.map((file) => [file.path, file]))
        setProject({
          ...loadedProject,
          files: loadedProject.files.map((file) => resultsByPath.get(file.path) ?? file),
        })
        setAnalysisComplete(true)
      } catch (error: unknown) {
        setProjectError(`Project loaded, but Python analysis failed: ${getErrorMessage(error)}`)
      }
    } catch (error: unknown) {
      setProjectError(getErrorMessage(error))
    } finally {
      setIsLoadingProject(false)
    }
  }

  const languages = project ? [...new Set(project.files.map((file) => file.language))].sort() : []
  const totalSize = project?.files.reduce((total, file) => total + file.size, 0) ?? 0

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="CodeCanopy home">
          <span className="brand__mark" aria-hidden="true">G</span>
          <span>CodeCanopy</span>
        </a>
        <div className="topbar__project">
          <span className="topbar__caption">Current project</span>
          <span className="topbar__project-name">{project?.name ?? 'Project Name'}</span>
        </div>
        <span className="topbar__environment">LOCAL</span>
      </header>

      <div className="dashboard-grid">
        <aside className="sidebar" aria-label="Project navigation">
          <div className="sidebar__heading">
            <h2>Project Tree</h2>
            <span>{project ? project.files.length : '—'}</span>
          </div>
          <div className="sidebar__tree">
            {isLoadingProject ? (
              <p className="tree-state" role="status">Loading files...</p>
            ) : project ? (
              <ProjectTree
                key={project.id}
                files={project.files}
                selectedPath={selectedFilePath}
                onSelect={setSelectedFilePath}
              />
            ) : (
              <p className="tree-state">No project loaded</p>
            )}
          </div>
          <div className="sidebar__status">
            <ApiStatus health={health} />
          </div>
        </aside>

        <section className="content-area" aria-labelledby="page-title">
          <header className="content-toolbar">
            <div>
              <p className="eyebrow">Workspace</p>
              <h1 id="page-title">Project Overview</h1>
            </div>
            <ProjectUpload onUploaded={handleUploaded} />
          </header>

          {projectError && <p className="error-banner" role="alert">{projectError}</p>}

          {isLoadingProject ? (
            <div className="loading-state" role="status">
              <span className="loading-state__dot" aria-hidden="true" />
              <span>Loading project and parsing Python files...</span>
            </div>
          ) : project ? (
            <>
              <dl className="project-stats">
                <div>
                  <dt>Files</dt>
                  <dd>{project.files.length}</dd>
                </div>
                <div>
                  <dt>Languages</dt>
                  <dd>{languages.length ? languages.join(', ') : '—'}</dd>
                </div>
                <div>
                  <dt>Total size</dt>
                  <dd>{formatSize(totalSize)}</dd>
                </div>
              </dl>

              {selectedFile ? (
                <FileDetails file={selectedFile} analysisComplete={analysisComplete} />
              ) : (
                <FileList files={project.files} onSelect={setSelectedFilePath} />
              )}
            </>
          ) : (
            <div className="empty-state">
              <span className="empty-state__marker" aria-hidden="true">ZIP</span>
              <h2>Upload a project to begin</h2>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}

interface FileListProps {
  files: ProjectFile[]
  onSelect: (path: string) => void
}

function FileList({ files, onSelect }: FileListProps) {
  const visibleFiles = files.slice(0, 100)

  return (
    <section className="file-list" aria-labelledby="file-list-heading">
      <div className="section-heading">
        <h2 id="file-list-heading">Files</h2>
        <span>{files.length}</span>
      </div>
      {files.length ? (
        <div className="file-list__scroll">
          <table>
            <thead>
              <tr><th>Path</th><th>Language</th><th>Size</th></tr>
            </thead>
            <tbody>
              {visibleFiles.map((file) => (
                <tr key={file.path}>
                  <td>
                    <button type="button" className="file-list__path" onClick={() => onSelect(file.path)}>
                      {file.path}
                    </button>
                  </td>
                  <td>{file.language}</td>
                  <td>{formatSize(file.size)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="tree-state">No files found</p>
      )}
      {files.length > visibleFiles.length && (
        <p className="file-list__note">Showing {visibleFiles.length} of {files.length} files</p>
      )}
    </section>
  )
}

interface FileDetailsProps {
  file: ProjectFile
  analysisComplete: boolean
}

function FileDetails({ file, analysisComplete }: FileDetailsProps) {
  return (
    <section className="file-details" aria-labelledby="file-details-heading">
      <p className="eyebrow">Selected file</p>
      <h2 id="file-details-heading">{file.path}</h2>
      <dl className="file-details__facts">
        <div><dt>Language</dt><dd>{file.language}</dd></div>
        <div><dt>Size</dt><dd>{formatSize(file.size)}</dd></div>
      </dl>
      {file.language === 'python' && analysisComplete && (
        <div className="parsed-analysis">
          <section className="parsed-analysis__section" aria-labelledby="functions-heading">
            <h3 id="functions-heading">Functions <span>{file.functions.length}</span></h3>
            {file.functions.length ? (
              <ul>
                {file.functions.map((functionInfo, index) => (
                  <li key={`${functionInfo.name}-${functionInfo.line_start}-${index}`}>
                    <span>{functionInfo.name}</span>
                    <code>L{functionInfo.line_start}-L{functionInfo.line_end}</code>
                  </li>
                ))}
              </ul>
            ) : <p>None detected</p>}
          </section>
          <section className="parsed-analysis__section" aria-labelledby="classes-heading">
            <h3 id="classes-heading">Classes <span>{file.classes.length}</span></h3>
            {file.classes.length ? (
              <ul>
                {file.classes.map((classInfo, index) => (
                  <li key={`${classInfo.name}-${classInfo.line_start}-${index}`}>
                    <span>{classInfo.name}</span>
                    <code>L{classInfo.line_start}-L{classInfo.line_end}</code>
                  </li>
                ))}
              </ul>
            ) : <p>None detected</p>}
          </section>
          <section className="parsed-analysis__section" aria-labelledby="imports-heading">
            <h3 id="imports-heading">Imports <span>{file.imports.length}</span></h3>
            {file.imports.length ? (
              <ul>{file.imports.map((moduleName, index) => <li key={`${moduleName}-${index}`}>{moduleName}</li>)}</ul>
            ) : <p>None detected</p>}
          </section>
        </div>
      )}
    </section>
  )
}
