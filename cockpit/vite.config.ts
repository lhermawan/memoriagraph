import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  base: './',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8085',
      '/recall': 'http://localhost:8085',
      '/retain': 'http://localhost:8085',
      '/health': 'http://localhost:8085',
    }
  }
})
