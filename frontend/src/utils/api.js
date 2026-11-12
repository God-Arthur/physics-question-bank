import axios from 'axios'
import { ElMessage } from 'element-plus'
import { cleanupUploadSessionNoAuth, cleanupPdfSessionNoAuth } from './uploadSession'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000
})

const isDev = import.meta.env.DEV

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    if (isDev) {
      console.debug('发送请求:', config.url, token ? '已携带 Token' : '无 Token')
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    const requestUrl = error.config?.url || ''
    const isLoginRequest = requestUrl.includes('/auth/login')
    const message = error.response?.data?.error || '请求失败'
    if (isDev) {
      console.error('请求错误:', error.response?.status, message)
    }
    // 登录失败的 401 是密码错误，不是登录过期，不能清掉 token 再跳回登录页
    if (!isLoginRequest) {
      ElMessage.error(message)
    }

    if (error.response?.status === 401 && !isLoginRequest) {
      if (isDev) {
        console.error('401 未授权，清除 token 并跳转登录')
      }
      // 登录过期时也尝试清理上传会话和PDF预览会话（不依赖 token）
      cleanupUploadSessionNoAuth()
      cleanupPdfSessionNoAuth()
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    
    return Promise.reject(error)
  }
)

export default api
