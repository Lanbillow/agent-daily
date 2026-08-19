<template>
  <n-card title="运行记录" size="small">
    <n-space vertical size="large">
      <n-space>
        <n-select v-model:value="job" :options="jobOptions" clearable placeholder="全部任务" style="width: 220px" />
        <n-button :loading="loading" @click="load">刷新</n-button>
      </n-space>
      <n-data-table :columns="columns" :data="runs" :loading="loading" :bordered="false" size="small" />
      <n-pagination v-model:page="page" :page-size="pageSize" :item-count="total" @update:page="load" />
    </n-space>
  </n-card>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue'
import { NTag, NTooltip } from 'naive-ui'
import { api } from '../api'
import type { Job, Run } from '../types'

const runs = ref<Run[]>([])
const jobs = ref<Job[]>([])
const job = ref<string | null>(null)
const loading = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const jobOptions = computed(() => jobs.value.map((item) => ({ label: item.id, value: item.id })))

const status = (value: string) => h(NTag, { size: 'small', type: value === 'success' ? 'success' : 'error' }, { default: () => value })
const columns = [
  { title: '任务', key: 'job', width: 180 },
  { title: '状态', key: 'status', width: 100, render: (row: Run) => status(row.status) },
  { title: '开始时间', key: 'start_time', width: 220, render: (row: Run) => row.start_time || '—' },
  { title: '结束时间', key: 'end_time', width: 220, render: (row: Run) => row.end_time || '—' },
  { title: '工件', key: 'artifacts', render: (row: Run) => row.artifacts?.join(', ') || '—' },
  {
    title: '错误', key: 'error', ellipsis: { tooltip: false },
    render: (row: Run) => row.error ? h(NTooltip, null, { trigger: () => row.error!.slice(0, 60), default: () => row.error }) : '—',
  },
]

async function load() {
  loading.value = true
  try {
    const data = await api.runs({ job: job.value || undefined, limit: pageSize, offset: (page.value - 1) * pageSize })
    runs.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}

watch(job, () => { page.value = 1; load() })
onMounted(async () => { jobs.value = await api.jobs(); await load() })
</script>
