import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwind from '@tailwindcss/vite'

const proxy = {
  '/api/tts': {
    target: process.env.ALAS_TTS_PROXY_TARGET ?? 'http://127.0.0.1:8000',
    proxyTimeout: 315_000,
  },
}

export default defineConfig({ plugins: [vue(), tailwind()], server: { proxy }, preview: { proxy } })
