import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  // 生产环境由 Nginx 反代，走同源相对路径；本地开发可通过 VITE_API_BASE 覆盖
  baseURL: import.meta.env.VITE_API_BASE || '',
  timeout: 15000,
})

// 请求拦截器：自动附加 token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('anime_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// 响应拦截器：统一处理 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // token 过期或无效，清除本地状态
      localStorage.removeItem('anime_token')
      localStorage.removeItem('anime_user')
      ElMessage.warning('登录已过期，请重新登录')
      // 跳转到登录页（避免在登录页重复跳转）
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default api
