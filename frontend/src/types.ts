export interface Job {
  id: string
  schedule: string
  description: string
  enabled: boolean
  last_status: string | null
}

export interface Run {
  job: string
  status: string
  start_time?: string
  end_time?: string
  artifacts?: string[]
  error?: string
}

export interface RunsResponse {
  total: number
  items: Run[]
}

export interface ArtifactMeta {
  name: string
  type: string
  date: string
  path: string
  created_at: string | null
}

export interface ArtifactsResponse {
  dates: string[]
  artifacts: ArtifactMeta[]
}

export interface ArtifactContent {
  name: string
  type: string
  date: string
  content: unknown
}

export interface ModelInfo {
  id: string
  provider: string
  default: boolean
  fallback: boolean
  enabled: boolean
  config: Record<string, unknown>
}

export interface ConfigResponse {
  config: Record<string, unknown>
  secrets: Record<string, boolean>
}

export interface SchedulerItem {
  job: string
  schedule: string
  plist_status: 'loaded' | 'not-loaded' | 'missing' | string
}

export interface LogTailResponse {
  file: string
  lines: string[]
}
