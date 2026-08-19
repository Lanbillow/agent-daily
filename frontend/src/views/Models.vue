<template>
  <n-space vertical size="large">
    <n-card title="模型路由" size="small">
      <n-alert type="info" :bordered="false">模型配置来自 config.yaml；密钥仅展示是否已配置。</n-alert>
    </n-card>
    <n-grid cols="1 720:2" x-gap="16" y-gap="16">
      <n-grid-item v-for="model in models" :key="model.id">
        <n-card :title="model.id" size="small">
          <template #header-extra><n-tag :type="model.enabled ? 'success' : 'default'">{{ model.enabled ? '可用' : '未配置' }}</n-tag></template>
          <n-descriptions label-placement="left" :column="1" size="small">
            <n-descriptions-item label="Provider">{{ model.provider }}</n-descriptions-item>
            <n-descriptions-item label="角色">
              <n-space><n-tag v-if="model.default" type="success" size="small">Primary</n-tag><n-tag v-if="model.fallback" type="warning" size="small">Fallback</n-tag></n-space>
            </n-descriptions-item>
          </n-descriptions>
          <n-code :code="JSON.stringify(model.config, null, 2)" language="json" word-wrap />
        </n-card>
      </n-grid-item>
    </n-grid>
  </n-space>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import type { ModelInfo } from '../types'
const models = ref<ModelInfo[]>([])
onMounted(async () => { models.value = await api.models() })
</script>
