<template>
  <n-space vertical size="large">
    <n-alert type="warning" :bordered="false">配置为只读展示。敏感值不会返回，密钥区域仅显示配置状态。</n-alert>
    <n-grid cols="1 900:3" x-gap="16" y-gap="16">
      <n-grid-item span="1 900:2">
        <n-card title="生效配置" size="small" :loading="loading"><n-code :code="configText" language="json" word-wrap /></n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card title="密钥状态" size="small" :loading="loading">
          <n-list>
            <n-list-item v-for="(ready, key) in data.secrets" :key="key">
              <n-thing :title="String(key)"><template #header-extra><n-tag :type="ready ? 'success' : 'default'" size="small">{{ ready ? '已配置' : '未配置' }}</n-tag></template></n-thing>
            </n-list-item>
          </n-list>
        </n-card>
      </n-grid-item>
    </n-grid>
  </n-space>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import type { ConfigResponse } from '../types'
const loading = ref(false)
const data = ref<ConfigResponse>({ config: {}, secrets: {} })
const configText = computed(() => JSON.stringify(data.value.config, null, 2))
onMounted(async () => { loading.value = true; try { data.value = await api.config() } finally { loading.value = false } })
</script>
