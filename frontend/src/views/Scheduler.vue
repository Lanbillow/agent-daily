<template>
  <n-card title="定时调度" size="small">
    <n-space vertical size="large">
      <n-alert type="info" :bordered="false">状态来自 macOS launchd。此页面只观察，不加载或卸载任务。</n-alert>
      <n-data-table :columns="columns" :data="items" :loading="loading" :bordered="false" size="small" />
    </n-space>
  </n-card>
</template>

<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { NTag } from 'naive-ui'
import { api } from '../api'
import type { SchedulerItem } from '../types'
const items = ref<SchedulerItem[]>([])
const loading = ref(false)
const columns = [
  { title: '任务', key: 'job' },
  { title: '执行时间', key: 'schedule', width: 140 },
  { title: 'launchd 状态', key: 'plist_status', width: 180, render: (row: SchedulerItem) => h(NTag, { size: 'small', type: row.plist_status === 'loaded' ? 'success' : 'warning' }, { default: () => row.plist_status }) },
]
onMounted(async () => { loading.value = true; try { items.value = await api.scheduler() } finally { loading.value = false } })
</script>
