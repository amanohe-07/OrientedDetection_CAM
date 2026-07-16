import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, apiError } from '@/api/client'
import type { SystemStatus } from '@/api/types'

export const useSystemStore = defineStore('system', () => {
  const status = ref<SystemStatus | null>(null)
  const loading = ref(false)
  const error = ref('')

  async function refresh() {
    loading.value = true
    error.value = ''
    try {
      status.value = await api.system()
    } catch (reason) {
      error.value = apiError(reason)
    } finally {
      loading.value = false
    }
  }

  return { status, loading, error, refresh }
})

