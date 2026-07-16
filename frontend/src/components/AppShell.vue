<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Menu,
  Radar,
  ScanLine,
  X,
} from '@lucide/vue'
import { useSystemStore } from '@/stores/system'

const route = useRoute()
const system = useSystemStore()
const mobileOpen = ref(false)
const title = computed(() => String(route.meta.title ?? '实验总览'))

const nav = [
  { to: '/', label: '实验总览', icon: BarChart3 },
  { to: '/detect', label: '单图检测', icon: ScanLine },
  { to: '/evaluate', label: '验证集评估', icon: Activity },
  { to: '/analysis', label: '错误归因', icon: AlertTriangle },
]

const modelTone = computed(() => {
  if (system.status?.model_state === 'ready') return 'ready'
  if (system.status?.model_state === 'error') return 'danger'
  return 'warning'
})
</script>

<template>
  <div class="app-shell">
    <button
      v-if="mobileOpen"
      class="sidebar-scrim"
      aria-label="关闭导航"
      @click="mobileOpen = false"
    />
    <aside class="sidebar" :class="{ open: mobileOpen }">
      <div class="brand">
        <span class="brand-mark"><Radar :size="22" stroke-width="2.3" /></span>
        <span class="brand-copy">
          <strong>舰瞰实验台</strong>
          <small>ORIENTED DETECTION</small>
        </span>
        <button class="icon-button sidebar-close" title="关闭导航" @click="mobileOpen = false">
          <X :size="19" />
        </button>
      </div>

      <nav class="primary-nav" aria-label="主导航">
        <RouterLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          @click="mobileOpen = false"
        >
          <component :is="item.icon" :size="19" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-status">
        <span class="status-caption">SYSTEM STATUS</span>
        <div class="status-row">
          <span>推理设备</span>
          <strong>{{ system.status?.device?.toUpperCase() ?? 'CPU' }}</strong>
        </div>
        <div class="status-row">
          <span>模型状态</span>
          <span class="status-badge" :class="modelTone">
            <i />
            {{ system.status?.model_state === 'ready' ? '已就绪' : '待配置' }}
          </span>
        </div>
      </div>
    </aside>

    <div class="workspace">
      <header class="topbar">
        <div class="topbar-title">
          <button class="icon-button menu-button" title="打开导航" @click="mobileOpen = true">
            <Menu :size="20" />
          </button>
          <div>
            <span>DOTA-v1.0 SHIP · YOLOv8n-OBB</span>
            <h1>{{ title }}</h1>
          </div>
        </div>
        <div class="topbar-state">
          <span class="live-dot" :class="{ offline: system.error }" />
          <span>
            <small>SERVICE NODE 01</small>
            {{ system.error ? 'API 离线' : 'CPU 服务在线' }}
          </span>
        </div>
      </header>
      <main class="page-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>
