<template>
  <n-grid cols="1 780:5" x-gap="16" y-gap="16">
    <n-grid-item span="1">
      <n-card title="日志文件" size="small">
        <n-menu :value="selected" :options="options" @update:value="selectLog" />
        <n-empty v-if="!files.length" description="暂无日志" />
      </n-card>
    </n-grid-item>
    <n-grid-item span="1 780:4">
      <n-card :title="selected || '日志内容'" size="small">
        <template #header-extra><n-button size="small" :disabled="!selected" :loading="loading" @click="loadTail">刷新</n-button></template>
        <pre v-if="lines.length" class="console">{{ lines.join('\n') }}</pre>
        <n-empty v-else description="选择日志文件查看最近 200 行" />
      </n-card>
    </n-grid-item>
  </n-grid>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
const files = ref<string[]>([])
const selected = ref<string | null>(null)
const lines = ref<string[]>([])
const loading = ref(false)
const options = computed(() => files.value.map((name) => ({ label: name, key: name })))
async function loadTail() { if (!selected.value) return; loading.value = true; try { lines.value = (await api.logTail(selected.value)).lines } finally { loading.value = false } }
async function selectLog(value: string) { selected.value = value; await loadTail() }
onMounted(async () => { files.value = await api.logs(); if (files.value.length) await selectLog(files.value[0]) })
</script>

<style scoped>
.console { min-height: 420px; max-height: 70vh; overflow: auto; margin: 0; padding: 14px; border-radius: 6px; background: #111827; color: #d1fae5; font: 12px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace; white-space: pre-wrap; }
</style>
