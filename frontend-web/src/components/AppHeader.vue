<template>
  <header class="app-header">
    <div class="app-header__inner">
      <router-link class="app-brand" to="/">
        <div class="app-brand__mark">AI</div>
        <div>
          <p class="app-brand__title">AI 小说生成器 Web</p>
          <p class="app-brand__subtitle">工作台、任务、项目详情与工具协作平台</p>
        </div>
      </router-link>

      <nav class="app-nav">
        <router-link
          v-for="item in navigationItems"
          :key="item.name"
          :to="item.to"
          class="app-nav__link"
          :class="{ 'is-active': route.name === item.name }"
        >
          {{ item.label }}
        </router-link>
      </nav>

      <div class="app-header__actions">
        <n-tag :type="backendStore.unavailable ? 'error' : 'success'" round>
          {{ backendStore.unavailable ? '后端离线' : '后端在线' }}
        </n-tag>
        <n-tag v-if="authStore.isAuthenticated" :type="authStore.isBackoffice ? 'warning' : 'success'" round>
          {{ authStore.displayName }} · {{ authStore.roleName }}
        </n-tag>
        <n-button
          v-if="authStore.isAuthenticated"
          tertiary
          type="primary"
          @click="router.push({ name: authStore.isBackoffice ? 'Settings' : 'Account' })"
        >
          {{ authStore.isBackoffice ? '后台控制台' : '账号中心' }}
        </n-button>
        <n-button v-if="authStore.isAuthenticated" secondary @click="handleLogout">
          退出
        </n-button>
        <n-button v-else type="primary" @click="router.push({ name: 'Login' })">
          登录 / 注册
        </n-button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NTag, useMessage } from 'naive-ui'
import { useAuthStore } from '../stores/auth'
import { useBackendStore } from '../stores/backend'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()
const backendStore = useBackendStore()

const navigationItems = computed(() => {
  const items = [
    { name: 'Home', label: '首页', to: { name: 'Home' } },
    { name: 'Workspace', label: '工作台', to: { name: 'Workspace' } },
    { name: 'Jobs', label: '任务中心', to: { name: 'Jobs' } },
    { name: 'Tools', label: '工具中心', to: { name: 'Tools' } },
    { name: 'Projects', label: '项目', to: { name: 'Projects' } }
  ]

  if (authStore.isAuthenticated) {
    items.push({
      name: 'Account',
      label: '账号',
      to: { name: 'Account' }
    })
  }

  if (authStore.isBackoffice) {
    items.push({ name: 'Settings', label: '设置', to: { name: 'Settings' } })
  }

  return items
})

function handleLogout() {
  authStore.logout()
  message.success('已退出登录')
  router.push({ name: 'Home' })
}
</script>
