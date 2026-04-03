import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export const useBackendStore = defineStore('backend', () => {
  const reachable = ref(true)
  const detail = ref('')
  const checkedAt = ref('')

  function setStatus(payload = {}) {
    reachable.value = payload.reachable !== false
    detail.value = payload.detail || ''
    checkedAt.value = payload.checkedAt || ''
  }

  const unavailable = computed(() => !reachable.value)

  return {
    reachable,
    unavailable,
    detail,
    checkedAt,
    setStatus
  }
})
