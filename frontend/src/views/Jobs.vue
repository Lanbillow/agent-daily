<template>
  <n-card title="任务列表（只读）" size="small">
    <n-data-table
      :columns="columns"
      :data="jobs"
      :loading="loading"
      :bordered="false"
      size="small"
    >
      <template #empty><n-empty description="暂无任务" /></template>
    </n-data-table>
  </n-card>
</template>

<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { NTag } from 'naive-ui'
import { api } from '../api'
import type { Job } from '../types'

const jobs = ref<Job[]>([])
const loading = ref(false)

const columns = [
  { title: 'Job ID', key: 'id' },
  { title: '描述', key: 'description', render: (row: Job) => row.description || '—' },
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
  {
    title: '最近状态',
    key: 'last_status',
    width: 120,
    render: (row: Job) =>
      row.last_status
        ? h(
            NTag,
            { type: row.last_status === 'success' ? 'success' : 'error', size: 'small' },
            { default: () => row.last_status },
          )
        : '—',
  },
]

onMounted(async () => {
  loading.value = true
  try {
    jobs.value = await api.jobs()
  } finally {
    loading.value = false
  }
})
</script>
