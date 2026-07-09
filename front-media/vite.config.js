import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // 开发态：把 API 请求代理到后端，避免跨域
    proxy: {
      '/auth': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
      '/recommend': 'http://localhost:8000',
    },
  },
})
