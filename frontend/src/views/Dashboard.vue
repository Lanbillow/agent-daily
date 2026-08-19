<template>
  <n-space vertical size="large">
    <n-card title="系统状态" size="small">
      <n-descriptions bordered :column="3" size="small">
        <n-descriptions-item label="运行状态">
          <n-tag :type="health.status === 'ok' ? 'success' : 'error'" size="small">
            {{ health.status === 'ok' ? '正常' : '异常' }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="版本">{{ health.version || '—' }}</n-descriptions-item>
        <n-descriptions-item label="API 连接">
          <n-tag :type="apiOk ? 'success' : 'error'" size="small">
            {{ apiOk ? '已连接' : '未连接' }}
          </n-tag>
        </n-descriptions-item>
      </n-descriptions>
    </n-card>

    <n-card title="任务状态" size="small">
      <n-data-table
        :columns="jobColumns"
        :data="jobs"
        :loading="loading"
        :bordered="false"
        size="small"
      >
        <template #empty><n-empty description="暂无任务" /></template>
      </n-data-table>
    </n-card>

    <n-card title="最近运行记录" size="small">
      <n-data-table
        :columns="runColumns"
        :data="runs"
        :loading="loading"
        :bordered="false"
        size="small"
      >
        <template #empty><n-empty description="暂无运行记录" /></template>
      </n-data-table>
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { NTag } from 'naive-ui'
import { api } from '../api'
import type { Job, Run } from '../types'

const health = ref<{ status: string; version: string }>({ status: 'unknown', version: '—' })
const apiOk = ref(true)
const jobs = ref<Job[]>([])
const runs = ref<Run[]>([])
const loading = ref(false)

const statusTag = (status: string | null) => {
  if (!status) return '—'
  return h(
    NTag,
    { type: status === 'success' ? 'success' : 'error', size: 'small' },
    { default: () => status },
  )
}

const jobColumns = [
  { title: 'Job ID', key: 'id' },
  { title: 'Schedule', key: 'schedule', width: 100 },
  {
    title: '启用',
    key: 'enabled',
    width: 80,
    render: (row: Job) =>
      h(
        NTag,
        { type: row.enabled ? 'success' : 'default', size: 'small' },
        { default: () => (row.enabled ? '启用' : '禁用') },
      ),
  },
  { title: '最近状态', key: 'last_status', width: 120, render: (row: Job) => statusTag(row.last_status) },
]

const runColumns = [
  { title: 'Job', key: 'job' },
  { title: '状态', key: 'status', width: 100, render: (row: Run) => statusTag(row.status) },
  { title: '开始时间', key: 'start_time', width: 220, render: (row: Run) => row.start_time || '—' },
  { title: 'Artifacts', key: 'artifacts', render: (row: Run) => (row.artifacts || []).join(', ') || '—' },
]

onMounted(async () => {
  loading.value = true
  try {
    const [h, j, r] = await Promise.all([api.health(), api.jobs(), api.runs({ limit: 10 })])
    health.value = h
    jobs.value = j
    runs.value = r.items
  } catch {
    apiOk.value = false
  } finally {
    loading.value = false
  }
})
</script>
