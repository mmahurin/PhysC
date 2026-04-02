import React, { useRef, useState } from 'react'
import { Upload, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface FileUploadZoneProps {
  id: string
  label: string
  required?: boolean
  accept?: string
  onFile: (file: File) => void
  file: File | null
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function FileUploadZone({
  id,
  label,
  required = false,
  accept = '.pdf,.jpg,.jpeg,.png',
  onFile,
  file,
}: FileUploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function handleFiles(files: FileList | null) {
    if (files && files.length > 0) {
      onFile(files[0])
    }
  }

  function onDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(true)
  }

  function onDragLeave(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(false)
  }

  function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  function onClick() {
    inputRef.current?.click()
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    handleFiles(e.target.files)
  }

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-foreground">
        {label}
        {required && (
          <span className="ml-1.5 inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
            Required
          </span>
        )}
      </label>

      <div
        onClick={onClick}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors',
          dragging
            ? 'border-primary bg-primary/5'
            : file
              ? 'border-green-400 bg-green-50'
              : 'border-border bg-muted/30 hover:border-primary/50 hover:bg-primary/5'
        )}
      >
        <input
          ref={inputRef}
          id={id}
          type="file"
          accept={accept}
          className="hidden"
          onChange={onInputChange}
        />

        {file ? (
          <div className="flex flex-col items-center gap-2 text-center">
            <CheckCircle2 className="h-8 w-8 text-green-500" />
            <p className="text-sm font-medium text-green-700 break-all max-w-xs">{file.name}</p>
            <p className="text-xs text-green-600">{formatBytes(file.size)}</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-center">
            <Upload className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-primary">Drag &amp; drop</span> or{' '}
              <span className="font-medium text-primary">browse</span>
            </p>
            <p className="text-xs text-muted-foreground">PDF, JPG, PNG supported</p>
          </div>
        )}
      </div>
    </div>
  )
}
