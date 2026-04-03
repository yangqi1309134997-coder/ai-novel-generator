import { createRouter, createWebHistory } from 'vue-router'

const AUTH_STORAGE_KEY = 'ai-novel-auth'

function hasAuthSession() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    const session = raw ? JSON.parse(raw) : null
    return Boolean(session?.accessToken)
  } catch {
    return false
  }
}

function hasBackofficeSession() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    const session = raw ? JSON.parse(raw) : null
    return Boolean(
      session?.user?.is_backoffice
      || session?.user?.is_admin
      || session?.user?.permissions?.includes?.('backoffice.view')
      || ['admin', 'operator', 'support'].includes(session?.user?.role)
    )
  } catch {
    return false
  }
}

const routes = [
  // Home page — no layout wrapper (uses legacy header/footer in its own view)
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/HomeView.vue'),
    meta: { layout: 'default' },
  },

  // Auth routes — AuthLayout (centered card, gradient background)
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { layout: 'auth' },
  },

  // Main app routes — MainLayout (sidebar + top bar)
  {
    path: '/workspace',
    name: 'Workspace',
    component: () => import('../views/WorkspaceView.vue'),
    meta: { requiresAuth: true, layout: 'main' },
  },
  {
    path: '/snowflake',
    redirect: { name: 'Workspace' },
  },
  {
    path: '/projects',
    name: 'Projects',
    component: () => import('../views/ProjectsView.vue'),
    meta: { requiresAuth: true, layout: 'main' },
  },
  {
    path: '/projects/:projectId',
    name: 'ProjectDetail',
    component: () => import('../views/ProjectDetailView.vue'),
    meta: { requiresAuth: true, layout: 'main' },
  },
  {
    path: '/jobs',
    name: 'Jobs',
    component: () => import('../views/JobsView.vue'),
    meta: { requiresAuth: true, layout: 'main' },
  },
  {
    path: '/tools',
    name: 'Tools',
    component: () => import('../views/ToolsView.vue'),
    meta: { requiresAuth: true, layout: 'main' },
  },
  {
    path: '/account',
    name: 'Account',
    component: () => import('../views/AccountView.vue'),
    meta: { requiresAuth: true, layout: 'main' },
  },

  // Legacy settings route — redirect to admin dashboard
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { requiresAuth: true, requiresBackoffice: true, layout: 'admin' },
  },

  // Admin routes — AdminLayout (admin sidebar + breadcrumb)
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: () => import('../views/admin/DashboardView.vue'),
    meta: { requiresAuth: true, requiresBackoffice: true, layout: 'admin' },
  },
  {
    path: '/admin/users',
    name: 'AdminUsers',
    component: () => import('../views/admin/UsersView.vue'),
    meta: { requiresAuth: true, requiresBackoffice: true, layout: 'admin' },
  },
  {
    path: '/admin/orders',
    name: 'AdminOrders',
    component: () => import('../views/admin/OrdersView.vue'),
    meta: { requiresAuth: true, requiresBackoffice: true, layout: 'admin' },
  },
  {
    path: '/admin/cdkeys',
    name: 'AdminCdkeys',
    component: () => import('../views/admin/CardCodesView.vue'),
    meta: { requiresAuth: true, requiresBackoffice: true, layout: 'admin' },
  },
  {
    path: '/admin/config',
    name: 'AdminConfig',
    component: () => import('../views/admin/SystemConfigView.vue'),
    meta: { requiresAuth: true, requiresBackoffice: true, layout: 'admin' },
  },
  {
    path: '/admin/prompts',
    name: 'AdminPrompts',
    component: () => import('../views/admin/PromptConfigView.vue'),
    meta: { requiresAuth: true, requiresBackoffice: true, layout: 'admin' },
  },
  {
    path: '/admin/logs',
    name: 'AdminLogs',
    component: () => import('../views/admin/AuditLogsView.vue'),
    meta: { requiresAuth: true, requiresBackoffice: true, layout: 'admin' },
  },

  // Catch-all 404
  {
    path: '/:pathMatch(.*)*',
    redirect: { name: 'Home' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const authenticated = hasAuthSession()
  const backoffice = hasBackofficeSession()

  if (to.meta.requiresAuth && !authenticated) {
    return {
      name: 'Login',
      query: { redirect: to.fullPath },
    }
  }

  if (to.name === 'Login' && authenticated) {
    return { name: 'Home' }
  }

  if (to.meta.requiresBackoffice && !backoffice) {
    return { name: 'Account' }
  }

  return true
})

export default router
