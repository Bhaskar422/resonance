import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// Two pages: the marketing site (/) and the workspace (/app). FastAPI serves the build;
// in development the API and run files are proxied to it.
const backend = 'http://127.0.0.1:8000';
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/',
  build: {
    outDir: resolve(__dirname, '../resonance/web/dist'),
    emptyOutDir: true,
    rollupOptions: { input: { site: resolve(__dirname, 'index.html'), app: resolve(__dirname, 'app.html') } },
  },
  server: { proxy: { '/api': backend, '/files': backend } },
});
