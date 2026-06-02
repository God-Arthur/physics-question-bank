import axios from 'axios'
import { ElMessage } from 'element-plus'
import { cleanupUploadSessionNoAuth, cleanupPdfSessionNoAuth } from './uploadSession'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      console.log('发送请求:', config.url, 'Token:', token.substring(0, 20) + '...')
    } else {
      console.log('发送请求:', config.url, '无 Token')
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
    const message = error.response?.data?.error || '请求失败'
    console.error('请求错误:', error.response?.status, message)
    ElMessage.error(message)
    
    if (error.response?.status === 401) {
      console.error('401 未授权，清除 token 并跳转登录')
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
