import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// `npm run build` writes straight into backend/static, which the Python server serves.
// Tailwind only emits the classes the code uses, so the shipped CSS is small (a few KB),
// and it is compiled here, never on the machine that runs the app.
// `npm run dev` proxies /api to a running backend (python run.py).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: { outDir: '../backend/static', emptyOutDir: true },
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})
