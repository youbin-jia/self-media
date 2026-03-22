import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 与 scripts/dev.sh 中 FRONTEND_PORT 对齐；strictPort 避免端口被占用时静默换端口
const devPort = Number(process.env.FRONTEND_PORT || process.env.VITE_DEV_PORT || 3000)

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number.isFinite(devPort) ? devPort : 3000,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
