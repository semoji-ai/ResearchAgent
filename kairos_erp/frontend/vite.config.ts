import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      "/api/auth/callback/google": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      }
    }
  },
  plugins: [react()],
})
