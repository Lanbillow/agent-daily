<template>
  <n-space vertical size="large">
    <n-card title="Artifacts（只读）" size="small">
      <n-space vertical size="small">
        <n-select
          v-model:value="selectedDate"
          :options="dateOptions"
          placeholder="选择日期"
          style="max-width: 240px"
          clearable
        />
        <n-data-table
          :columns="columns"
          :data="artifacts"
          :loading="loading"
          :bordered="false"
          size="small"
        >
          <template #empty><n-empty description="暂无工件" /></template>
        </n-data-table>
      </n-space>
    </n-card>

    <n-card v-if="preview" title="内容预览" size="small">
      <template #header-extra>
        <n-tag size="small">{{ preview.name }}.{{ preview.type }}</n-tag>
      </template>
      <pre class="preview">{{ previewText }}</pre>
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue'
import { NButton, NTag } from 'naive-ui'
import { api } from '../api'
import type { ArtifactMeta } from '../types'

const dates = ref<string[]>([])
const artifacts = ref<ArtifactMeta[]>([])
const selectedDate = ref<string | null>(null)
const loading = ref(false)
const preview = ref<{ name: string; type: string; content: unknown } | null>(null)

const dateOptions = computed(() => dates.value.map((d) => ({ label: d, value: d })))

const columns = [
  { title: '名称', key: 'name' },
  {
    title: '类型',
    key: 'type',
    width: 100,
    render: (row: ArtifactMeta) =>
      h(
        NTag,
        { size: 'small', bordered: false },
        { default: () => row.type },
      ),
  },
  { title: '创建时间', key: 'created_at', width: 220, render: (row: ArtifactMeta) => row.created_at || '—' },
  {
    title: '预览',
    key: 'action',
    width: 90,
    render: (row: ArtifactMeta) =>
      h(
        NButton,
        { size: 'tiny', onClick: () => loadPreview(row) },
        { default: () => '预览' },
      ),
  },
]

const previewText = computed(() => {
  if (!preview.value) return ''
  const c = preview.value.content
  return typeof c === 'string' ? c : JSON.stringify(c, null, 2)
})

async function loadDates() {
  const data = await api.artifacts()
  dates.value = data.dates
  if (data.dates.length && !selectedDate.value) {
    selectedDate.value = data.dates[data.dates.length - 1]
  }
}

async function loadArtifacts() {
  if (!selectedDate.value) {
    artifacts.value = []
    return
  }
  loading.value = true
  try {
    const data = await api.artifacts(selectedDate.value)
    artifacts.value = data.artifacts
  } finally {
    loading.value = false
  }
}

async function loadPreview(row: ArtifactMeta) {
  preview.value = await api.artifact(row.date, row.name)
}

watch(selectedDate, () => {
  preview.value = null
  loadArtifacts()
})

onMounted(async () => {
  await loadDates()
  await loadArtifacts()
})
</script>

<style scoped>
.preview {
  margin: 0;
  padding: 12px;
  background: #f7f7f7;
  border-radius: 4px;
  max-height: 480px;
  overflow: auto;
  font-size: 13px;
  white-space: pre-wrap;
}
</style>
