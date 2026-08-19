<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-layout has-sider style="height: 100vh">
      <n-layout-sider bordered width="210" :native-scrollbar="false">
        <div class="logo">Agent Daily</div>
        <n-menu
          :value="activeKey"
          :options="menuOptions"
          @update:value="onMenu"
        />
      </n-layout-sider>
      <n-layout>
        <n-layout-header bordered class="header">
          <span class="header-title">个人 AI Agent 控制台</span>
          <span class="header-sub">Control Plane · 只读模式</span>
        </n-layout-header>
        <n-layout-content class="content" :native-scrollbar="false">
          <router-view />
        </n-layout-content>
      </n-layout>
    </n-layout>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const menuOptions = [
  { label: '总览', key: '/' },
  { label: '任务', key: '/jobs' },
  { label: '运行记录', key: '/runs' },
  { label: '工件', key: '/artifacts' },
  { label: '模型', key: '/models' },
  { label: '调度', key: '/scheduler' },
  { label: '日志', key: '/logs' },
  { label: '配置', key: '/config' },
]

const activeKey = computed(() => route.path)
const onMenu = (key: string) => router.push(key)

const themeOverrides = {
  common: { primaryColor: '#2080f0' },
}
</script>

<style>
body {
  margin: 0;
  background: #f5f7fa;
  color: #1f2937;
}
.logo {
  padding: 16px;
  font-size: 18px;
  font-weight: 600;
}
.header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  height: 52px;
}
.header-title {
  font-size: 16px;
  font-weight: 500;
}
.header-sub {
  font-size: 12px;
  color: #999;
}
.content {
  padding: 20px;
  background: #f5f7fa;
}

@media (max-width: 720px) {
  .header-sub { display: none; }
  .content { padding: 12px; }
}
</style>
