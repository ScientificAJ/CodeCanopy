import { useState, type FormEvent } from 'react'
import { uploadProject } from '../services/api'
import type { ProjectUploadResponse } from '../types/api'

const MAX_UPLOAD_BYTES = 50 * 1024 * 1024

interface ProjectUploadProps {
  onUploaded: (project: ProjectUploadResponse) => Promise<void>
}

export default function ProjectUpload({ onUploaded }: ProjectUploadProps) {
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [project, setProject] = useState<ProjectUploadResponse | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file) return

    setError(null)
    setProject(null)
    if (file.size > MAX_UPLOAD_BYTES) {
      setError('ZIP archives must be 50 MiB or smaller.')
      return
    }

    setIsUploading(true)
    try {
      const uploadedProject = await uploadProject(file)
      setProject(uploadedProject)
      await onUploaded(uploadedProject)
    } catch (uploadError: unknown) {
      setError(uploadError instanceof Error ? uploadError.message : 'Upload failed.')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="project-upload">
      <form className="project-upload__form" onSubmit={handleSubmit}>
        <label className="project-upload__picker">
          <span>Project ZIP</span>
          <input
            type="file"
            accept=".zip,application/zip"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null)
              setError(null)
              setProject(null)
            }}
          />
        </label>
        <button type="submit" disabled={!file || isUploading}>
          {isUploading ? 'Uploading...' : 'Upload project'}
        </button>
      </form>
      <p className="project-upload__hint">ZIP archive, up to 50 MiB</p>
      {error && <p className="project-upload__message project-upload__message--error" role="alert">{error}</p>}
      {project && (
        <p className="project-upload__message" role="status">
          Uploaded {project.file_count} files · project <code>{project.project_id}</code>
        </p>
      )}
    </div>
  )
}