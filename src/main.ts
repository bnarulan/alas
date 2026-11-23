import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { makeRouter } from './router'
import { usePlatform } from './stores/platform'
import './style.css'

async function start() {
  const app = createApp(App)
  const pinia = createPinia()
  app.use(pinia)
  const store = usePlatform(pinia)
  await store.initialize()
  document.documentElement.lang = store.locale
  const router = makeRouter(store)
  app.use(router)
  await router.isReady()
  app.mount('#app')
}

void start()
