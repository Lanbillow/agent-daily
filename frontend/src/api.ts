import axios from 'axios'
import type {
  ArtifactContent,
  ArtifactsResponse,
  ConfigResponse,
  Job,
  LogTailResponse,
  ModelInfo,
  RunsResponse,
  SchedulerItem,
} from './types'

const client = axios.create({ baseURL: '/api', timeout: 10000 })

export const api = {
  health: () => client.get<{ status: string; version: string }>('/health').then((r) => r.data),
  jobs: () => client.get<Job[]>('/jobs').then((r) => r.data),
  runs: (params?: { job?: string; limit?: number; offset?: number }) =>
    client.get<RunsResponse>('/runs', { params }).then((r) => r.data),
  artifacts: (date?: string) =>
    client.get<ArtifactsResponse>('/artifacts', { params: { date } }).then((r) => r.data),
  artifact: (date: string, name: string) =>
    client.get<ArtifactContent>(`/artifacts/${date}/${encodeURIComponent(name)}`).then((r) => r.data),
  models: () => client.get<ModelInfo[]>('/models').then((r) => r.data),
  config: () => client.get<ConfigResponse>('/config').then((r) => r.data),
  scheduler: () => client.get<SchedulerItem[]>('/scheduler/status').then((r) => r.data),
  logs: () => client.get<string[]>('/logs').then((r) => r.data),
  logTail: (name: string, tail = 200) =>
    client.get<LogTailResponse>(`/logs/${encodeURIComponent(name)}`, { params: { tail } }).then((r) => r.data),
}
