import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Single-page demo app talking to a separate FastAPI backend.
// A dev proxy forwards /api to the backend so the browser stays same-origin
// during development; in production VITE_API_BASE_URL points at the backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
