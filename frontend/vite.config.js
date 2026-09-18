import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发阶段：/api 和 /static 全部转发给后端（默认 localhost:8000），不用配 CORS
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
