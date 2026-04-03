import { reactive } from 'vue'
import { defineStore } from 'pinia'
import { apiClient } from '../api'

export const usePlatformStore = defineStore('platform', () => {
  const policy = reactive({
    commercial_mode: true,
    generation_mode: 'free',
    allow_registration: true,
    customer_can_manage_api: false,
    customer_can_manage_prompts: false
  })

  async function refreshPolicy() {
    const response = await apiClient.getPublicPolicy()
    Object.assign(policy, response.data || {})
    return policy
  }

  return {
    policy,
    refreshPolicy
  }
})
