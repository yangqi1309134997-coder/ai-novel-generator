<template>
  <n-layout has-sider class="admin-layout">
    <!-- Admin sidebar -->
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="240"
      :collapsed="collapsed"
      show-trigger
      @collapse="collapsed = true"
      @expand="collapsed = false"
      class="admin-layout__sider"
    >
      <div class="admin-logo" :class="{ 'admin-logo--collapsed': collapsed }">
        <div class="admin-logo__mark">
          <n-icon :size="18" color="#fff"><settings-outline /></n-icon>
        </div>
        <transition name="fade">
          <span v-if="!collapsed" class="admin-logo__text">管理面板</span>
        </transition>
      </div>

      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="20"
        :options="menuOptions"
        :value="activeKey"
        :root-indent="16"
        @update:value="handleMenuSelect"
      />
    </n-layout-sider>

    <n-layout>
      <!-- Breadcrumb header -->
      <n-layout-header bordered class="admin-layout__header">
        <n-breadcrumb class="admin-breadcrumb">
          <n-breadcrumb-item @click="router.push({ name: 'Workspace' })">
            首页
          </n-breadcrumb-item>
          <n-breadcrumb-item>管理面板</n-breadcrumb-item>
          <n-breadcrumb-item>{{ currentTitle }}</n-breadcrumb-item>
        </n-breadcrumb>
        <div class="admin-header__right">
          <n-button quaternary size="small" @click="router.push({ name: 'Workspace' })">
            返回前台
          </n-button>
          <n-tag size="small" round>{{ authStore.displayName }}</n-tag>
        </div>
      </n-layout-header>

      <!-- Content -->
      <n-layout-content class="admin-layout__content">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup>
import { computed, h, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NBreadcrumb,
  NBreadcrumbItem,
  NButton,
  NIcon,
  NLayout,
  NLayoutContent,
  NLayoutHeader,
  NLayoutSider,
  NMenu,
  NTag,
} from 'naive-ui'
import {
  SpeedometerOutline,
  PeopleOutline,
  ReceiptOutline,
  KeyOutline,
  SettingsOutline,
  DocumentTextOutline,
  NewspaperOutline,
} from '@vicons/ionicons5'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const collapsed = ref(false)

function renderIcon(icon) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions = [
  { label: '仪表盘', key: 'dashboard', icon: renderIcon(SpeedometerOutline) },
  { label: '用户管理', key: 'users', icon: renderIcon(PeopleOutline) },
  { label: '订单管理', key: 'orders', icon: renderIcon(ReceiptOutline) },
  { label: '卡密管理', key: 'cdkeys', icon: renderIcon(KeyOutline) },
  { label: '系统配置', key: 'config', icon: renderIcon(SettingsOutline) },
  { label: '提示词管理', key: 'prompts', icon: renderIcon(DocumentTextOutline) },
  { label: '系统日志', key: 'logs', icon: renderIcon(NewspaperOutline) },
]

const routeKeyMap = {
  AdminDashboard: 'dashboard',
  AdminUsers: 'users',
  AdminOrders: 'orders',
  AdminCdkeys: 'cdkeys',
  AdminConfig: 'config',
  AdminPrompts: 'prompts',
  AdminLogs: 'logs',
}

const keyRouteMap = {
  dashboard: { name: 'AdminDashboard' },
  users: { name: 'AdminUsers' },
  orders: { name: 'AdminOrders' },
  cdkeys: { name: 'AdminCdkeys' },
  config: { name: 'AdminConfig' },
  prompts: { name: 'AdminPrompts' },
  logs: { name: 'AdminLogs' },
}

const titleMap = {
  dashboard: '仪表盘',
  users: '用户管理',
  orders: '订单管理',
  cdkeys: '卡密管理',
  config: '系统配置',
  prompts: '提示词管理',
  logs: '系统日志',
}

const activeKey = computed(() => routeKeyMap[route.name] || 'dashboard')
const currentTitle = computed(() => titleMap[activeKey.value] || '管理面板')

function handleMenuSelect(key) {
  const target = keyRouteMap[key]
  if (target) {
    router.push(target)
  }
}
</script>

<style scoped>
.admin-layout {
  min-height: 100vh;
}

.admin-layout__sider {
  background: #ffffff;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
}

.admin-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 16px;
  border-bottom: 1px solid #f1f5f9;
  overflow: hidden;
  white-space: nowrap;
}

.admin-logo--collapsed {
  justify-content: center;
  padding: 20px 0 16px;
}

.admin-logo__mark {
  width: 36px;
  height: 36px;
  min-width: 36px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.admin-logo__text {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}

.admin-layout__header {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #ffffff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.admin-breadcrumb {
  font-size: 14px;
}

.admin-header__right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.admin-layout__content {
  padding: 24px;
  min-height: calc(100vh - 52px);
  background: #f8fafc;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .admin-layout__content {
    padding: 16px;
  }
}
</style>
