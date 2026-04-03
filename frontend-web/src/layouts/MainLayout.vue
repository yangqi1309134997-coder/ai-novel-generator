<template>
  <n-layout has-sider class="main-layout">
    <!-- Desktop sidebar -->
    <n-layout-sider
      v-if="!isMobile"
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="220"
      :collapsed="collapsed"
      show-trigger
      @collapse="collapsed = true"
      @expand="collapsed = false"
      class="main-layout__sider"
    >
      <div class="sider-logo" :class="{ 'sider-logo--collapsed': collapsed }">
        <div class="sider-logo__mark">AI</div>
        <transition name="fade">
          <span v-if="!collapsed" class="sider-logo__text">AI Novel</span>
        </transition>
      </div>

      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="activeKey"
        :root-indent="16"
        @update:value="handleMenuSelect"
      />
    </n-layout-sider>

    <n-layout>
      <!-- Top bar -->
      <n-layout-header bordered class="main-layout__header">
        <div class="header-left">
          <n-button v-if="isMobile" quaternary @click="showMobileMenu = true">
            <template #icon>
              <n-icon><menu-outline /></n-icon>
            </template>
          </n-button>
          <h2 class="header-title">{{ currentTitle }}</h2>
        </div>
        <div class="header-right">
          <n-tag :type="backendStore.unavailable ? 'error' : 'success'" round size="small">
            {{ backendStore.unavailable ? '离线' : '在线' }}
          </n-tag>
          <n-tag v-if="authStore.isAuthenticated" size="small" round>
            {{ authStore.displayName }}
          </n-tag>
          <n-button
            v-if="authStore.isAuthenticated"
            quaternary
            size="small"
            @click="handleLogout"
          >
            退出
          </n-button>
        </div>
      </n-layout-header>

      <!-- Backend alert -->
      <div v-if="!backendReachable" class="backend-alert-wrapper">
        <n-alert type="error" :show-icon="false" class="app-banner">
          <div class="app-banner__content">
            <div class="app-banner__text">
              <strong>后端服务不可达</strong>
              <div>{{ backendDetail || '请确认后端服务已启动。' }}</div>
            </div>
            <n-button tertiary size="small" @click="checkBackend">重新检测</n-button>
          </div>
        </n-alert>
      </div>

      <!-- Content -->
      <n-layout-content class="main-layout__content">
        <router-view />
      </n-layout-content>
    </n-layout>

    <!-- Mobile drawer menu -->
    <n-drawer v-model:show="showMobileMenu" placement="left" :width="260">
      <n-drawer-content title="导航菜单" :native-scrollbar="false">
        <n-menu
          :options="menuOptions"
          :value="activeKey"
          @update:value="handleMobileMenuSelect"
        />
      </n-drawer-content>
    </n-drawer>

    <!-- Mobile bottom tab bar -->
    <div v-if="isMobile" class="mobile-tab-bar">
      <div
        v-for="tab in mobileTabs"
        :key="tab.key"
        class="mobile-tab-item"
        :class="{ 'mobile-tab-item--active': activeKey === tab.key }"
        @click="handleMenuSelect(tab.key)"
      >
        <n-icon :size="20">
          <component :is="tab.icon" />
        </n-icon>
        <span class="mobile-tab-item__label">{{ tab.label }}</span>
      </div>
    </div>
  </n-layout>
</template>

<script setup>
import { computed, h, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NButton,
  NDrawer,
  NDrawerContent,
  NIcon,
  NLayout,
  NLayoutContent,
  NLayoutHeader,
  NLayoutSider,
  NMenu,
  NTag,
  useMessage,
} from 'naive-ui'
import {
  DesktopOutline,
  CreateOutline,
  FolderOutline,
  ListOutline,
  ConstructOutline,
  PersonOutline,
  SettingsOutline,
  MenuOutline,
} from '@vicons/ionicons5'
import { useAuthStore } from '../stores/auth'
import { useBackendStore } from '../stores/backend'
import { apiClient, API_BASE_URL } from '../api'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const authStore = useAuthStore()
const backendStore = useBackendStore()

const collapsed = ref(false)
const showMobileMenu = ref(false)
const isMobile = ref(window.innerWidth < 768)

window.addEventListener('resize', () => {
  isMobile.value = window.innerWidth < 768
})

const backendReachable = computed(() => backendStore.reachable)
const backendDetail = computed(() => backendStore.detail)

function renderIcon(icon) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions = computed(() => {
  const items = [
    { label: '工作台', key: 'workspace', icon: renderIcon(DesktopOutline) },
    { label: '新建小说', key: 'new-novel', icon: renderIcon(CreateOutline) },
    { label: '项目中心', key: 'projects', icon: renderIcon(FolderOutline) },
    { label: '任务中心', key: 'jobs', icon: renderIcon(ListOutline) },
    { label: '工具中心', key: 'tools', icon: renderIcon(ConstructOutline) },
    { label: '账号中心', key: 'account', icon: renderIcon(PersonOutline) },
  ]
  if (authStore.isBackoffice) {
    items.push({
      label: '管理员入口',
      key: 'admin',
      icon: renderIcon(SettingsOutline),
    })
  }
  return items
})

const mobileTabs = computed(() => [
  { key: 'workspace', label: '工作台', icon: DesktopOutline },
  { key: 'projects', label: '项目', icon: FolderOutline },
  { key: 'jobs', label: '任务', icon: ListOutline },
  { key: 'tools', label: '工具', icon: ConstructOutline },
  { key: 'account', label: '我的', icon: PersonOutline },
])

const routeKeyMap = {
  Workspace: 'workspace',
  Projects: 'projects',
  ProjectDetail: 'projects',
  Jobs: 'jobs',
  Tools: 'tools',
  Account: 'account',
  Settings: 'admin',
}

const keyRouteMap = {
  workspace: { name: 'Workspace' },
  'new-novel': { name: 'Workspace' },
  projects: { name: 'Projects' },
  jobs: { name: 'Jobs' },
  tools: { name: 'Tools' },
  account: { name: 'Account' },
  admin: { name: 'AdminDashboard' },
}

const activeKey = computed(() => routeKeyMap[route.name] || 'workspace')

const titleMap = {
  workspace: '工作台',
  'new-novel': '新建小说',
  projects: '项目中心',
  jobs: '任务中心',
  tools: '工具中心',
  account: '账号中心',
  admin: '管理员面板',
}

const currentTitle = computed(() => titleMap[activeKey.value] || 'AI Novel')

function handleMenuSelect(key) {
  const target = keyRouteMap[key]
  if (target) {
    router.push(target)
  }
  showMobileMenu.value = false
}

function handleMobileMenuSelect(key) {
  handleMenuSelect(key)
}

async function checkBackend() {
  try {
    const response = await apiClient.healthCheck()
    backendStore.setStatus({
      reachable: response.status === 'healthy',
      detail: response.status === 'healthy' ? '' : '后端健康检查异常',
      checkedAt: new Date().toISOString(),
    })
  } catch (error) {
    backendStore.setStatus({
      reachable: false,
      detail: error?.detail || error?.message || '请确认后端已启动。',
      checkedAt: new Date().toISOString(),
    })
  }
}

function handleLogout() {
  authStore.logout()
  message.success('已退出登录')
  router.push({ name: 'Login' })
}
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
}

.main-layout__sider {
  background: #ffffff;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.sider-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 16px;
  border-bottom: 1px solid #f1f5f9;
  overflow: hidden;
  white-space: nowrap;
}

.sider-logo--collapsed {
  justify-content: center;
  padding: 20px 0 16px;
}

.sider-logo__mark {
  width: 36px;
  height: 36px;
  min-width: 36px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-weight: 800;
  font-size: 14px;
  letter-spacing: 0.04em;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.sider-logo__text {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}

.main-layout__header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #ffffff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.main-layout__content {
  padding: 24px;
  min-height: calc(100vh - 56px);
  background: #f8fafc;
}

.backend-alert-wrapper {
  padding: 16px 24px 0;
  background: #f8fafc;
}

.app-banner {
  border-radius: 12px;
}

.app-banner__content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.app-banner__text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
}

/* Mobile bottom tab bar */
.mobile-tab-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: #ffffff;
  border-top: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-around;
  z-index: 100;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);
}

.mobile-tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 4px 8px;
  cursor: pointer;
  color: #94a3b8;
  transition: color 0.2s ease;
}

.mobile-tab-item--active {
  color: #6366f1;
}

.mobile-tab-item__label {
  font-size: 10px;
  line-height: 1;
}

/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .main-layout__content {
    padding: 16px;
    padding-bottom: 76px;
  }
}
</style>
