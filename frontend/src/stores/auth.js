import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../utils/api'
import { cleanupUploadSessionAuth, cleanupPdfSessionAuth } from '../utils/uploadSession'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('token'))

  const isLoggedIn = computed(() => !!token.value)
  const userRole = computed(() => user.value?.role || '')
  const needChangePassword = computed(() => user.value && !user.value.password_changed)

  async function login(username, password) {
    const res = await api.post('/auth/login', { username, password })
    token.value = res.access_token
    user.value = res.user
    localStorage.setItem('token', res.access_token)
    return res
  }

  async function logout() {
    // 主动退出：先清理上传会话和PDF预览会话（此时 token 仍可用）
    try {
      await cleanupUploadSessionAuth(api)
    } catch {
      // 忽略
    }
    try {
      await cleanupPdfSessionAuth(api)
    } catch {
      // 忽略
    }
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  async function fetchUser() {
    if (!token.value) return null
    try {
      const res = await api.get('/auth/me')
      user.value = res.user
      return res.user
    } catch (error) {
      await logout()
      throw error
    }
  }

  return {
    user,
    token,
    isLoggedIn,
    userRole,
    needChangePassword,
    login,
    logout,
    fetchUser
  }
})
