import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // needed for docker
    port: 3000,
    allowedHosts: [
      'trickyclip.com',
      'localhost',
      '127.0.0.1'
    ],
    proxy: {
        '/api': {
            target: 'http://backend:8000',
            changeOrigin: true
        }
    }
  }
})

