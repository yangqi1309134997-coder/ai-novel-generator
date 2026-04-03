import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { AUTH_STORAGE_KEY, apiClient } from '../api'

function readStoredSession() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const accessToken = ref('')
  const refreshToken = ref('')

  function persist() {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({
      user: user.value,
      accessToken: accessToken.value,
      refreshToken: refreshToken.value
    }))
  }

  function hydrate() {
    const session = readStoredSession()
    user.value = session.user || null
    accessToken.value = session.accessToken || ''
    refreshToken.value = session.refreshToken || ''
  }

  function setSession(payload) {
    user.value = payload.user || null
    accessToken.value = payload.access_token || accessToken.value
    refreshToken.value = payload.refresh_token || refreshToken.value
    persist()
  }

  async function refreshProfile() {
    if (!accessToken.value) {
      return null
    }
    const response = await apiClient.getCurrentUser()
    user.value = response.data || null
    persist()
    return user.value
  }

  async function login(credentials) {
    const response = await apiClient.login(credentials)
    setSession(response)
    return response
  }

  async function register(payload) {
    const response = await apiClient.register(payload)
    setSession(response)
    return response
  }

  function logout() {
    user.value = null
    accessToken.value = ''
    refreshToken.value = ''
    localStorage.removeItem(AUTH_STORAGE_KEY)
  }

  const isAuthenticated = computed(() => Boolean(accessToken.value))
  const displayName = computed(() => user.value?.username || user.value?.email || '未登录')
  const role = computed(() => user.value?.role || 'customer')
  const roleName = computed(() => user.value?.role_name || '客户用户')
  const permissions = computed(() => Array.isArray(user.value?.permissions) ? user.value.permissions : [])
  const isAdmin = computed(() => Boolean(user.value?.is_admin || role.value === 'admin'))
  const isBackoffice = computed(() => Boolean(user.value?.is_backoffice || permissions.value.includes('backoffice.view')))
  const subscriptionTier = computed(() => user.value?.subscription_tier || 'free')
  const subscriptionName = computed(() => user.value?.subscription_name || '免费用户')
  const remainingQuota = computed(() => Number(user.value?.remaining_quota) || 0)
  const canGenerate = computed(() => Boolean(user.value?.can_generate))
  const generationMessage = computed(() => user.value?.generation_message || '')

  function hasPermission(permission) {
    return permissions.value.includes(permission)
  }

  hydrate()

  return {
    user,
    accessToken,
    refreshToken,
    isAuthenticated,
    displayName,
    role,
    roleName,
    permissions,
    isAdmin,
    isBackoffice,
    subscriptionTier,
    subscriptionName,
    remainingQuota,
    canGenerate,
    generationMessage,
    hasPermission,
    hydrate,
    setSession,
    refreshProfile,
    login,
    register,
    logout
  }
})
