import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Local only: the dev server binds to localhost and proxies /api to the
// Express process so the browser sees a single origin.
export default defineConfig({
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8731' },
  },
  build: { outDir: 'dist' },
  plugins: [react()],
});
