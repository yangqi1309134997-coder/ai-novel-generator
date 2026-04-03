<template>
  <n-config-provider :theme-overrides="lightThemeOverrides">
    <n-message-provider>
      <div id="app" class="app-shell">
        <component :is="layoutComponent">
          <template #default>
            <router-view v-slot="{ Component, route: currentRoute }">
              <transition name="page" mode="out-in">
                <component :is="Component" :key="currentRoute.path" />
              </transition>
            </router-view>
          </template>
        </component>
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { NConfigProvider, NMessageProvider } from 'naive-ui'
import { lightThemeOverrides } from './theme'
import { API_BASE_URL, BACKEND_STATUS_EVENT, apiClient } from './api'
import { useAuthStore } from './stores/auth'
import { useBackendStore } from './stores/backend'
import { usePlatformStore } from './stores/platform'

import MainLayout from './layouts/MainLayout.vue'
import AuthLayout from './layouts/AuthLayout.vue'
import AdminLayout from './layouts/AdminLayout.vue'

const route = useRoute()
const backendStore = useBackendStore()
const authStore = useAuthStore()
const platformStore = usePlatformStore()
const backendBaseUrl = API_BASE_URL
let timer = null

// Select layout based on route meta
const layoutComponent = computed(() => {
  const layout = route.meta?.layout
  if (layout === 'auth') return AuthLayout
  if (layout === 'admin') return AdminLayout
  if (layout === 'main') return MainLayout
  // Default: no layout wrapper (bare route like Home)
  return DefaultLayout
})

// Minimal pass-through layout for routes without a specific layout
const DefaultLayout = {
  name: 'DefaultLayout',
  render() {
    return this.$slots.default?.()
  },
}

function applyBackendStatus(payload = {}) {
  backendStore.setStatus({
    reachable: payload.reachable !== false,
    detail: payload.detail || '',
    checkedAt: payload.checkedAt || new Date().toISOString(),
  })
}

function handleBackendEvent(event) {
  applyBackendStatus(event.detail)
}

async function checkBackend() {
  try {
    const response = await apiClient.healthCheck()
    applyBackendStatus({
      reachable: response.status === 'healthy',
      detail: response.status === 'healthy' ? '' : '后端健康检查异常',
      checkedAt: new Date().toISOString(),
    })
  } catch (error) {
    applyBackendStatus({
      reachable: false,
      detail: error?.detail || error?.message || `请确认 ${backendBaseUrl} 已启动。`,
      checkedAt: new Date().toISOString(),
    })
  }
}

onMounted(() => {
  checkBackend()
  platformStore.refreshPolicy().catch(() => {})
  if (authStore.isAuthenticated) {
    authStore.refreshProfile().catch(() => {})
  }
  window.addEventListener(BACKEND_STATUS_EVENT, handleBackendEvent)
  timer = window.setInterval(() => {
    checkBackend()
    platformStore.refreshPolicy().catch(() => {})
    if (authStore.isAuthenticated) {
      authStore.refreshProfile().catch(() => {})
    }
  }, 15000)
})

onUnmounted(() => {
  window.removeEventListener(BACKEND_STATUS_EVENT, handleBackendEvent)
  if (timer) {
    window.clearInterval(timer)
  }
})
</script>

<style>
@import './assets/main.css';

.app-shell {
  min-height: 100vh;
}
</style>
