<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { BookOpen, Bookmark, ClipboardList, LayoutDashboard, LogOut, Menu, PanelTop, RotateCcw, UserRound, UsersRound, X, ChartNoAxesColumnIncreasing } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { usePlatform } from '../stores/platform'
import BrandMark from './BrandMark.vue'
import LanguageSwitch from './LanguageSwitch.vue'
import ConfirmDialog from './ConfirmDialog.vue'

const store = usePlatform()
const route = useRoute()
const router = useRouter()
const dialog = ref<InstanceType<typeof ConfirmDialog>>()
const mobileOpen = ref(false)
const menuToggle = ref<HTMLButtonElement>()
const firstNav = ref<HTMLElement>()
const studentLinks = [
  { name: 'student', kk: 'Басты бет', ru: 'Главная', icon: LayoutDashboard, related: [] },
  { name: 'catalog', kk: 'Сабақтар', ru: 'Уроки', icon: BookOpen, related: ['lesson'] },
  { name: 'vocabulary', kk: 'Менің сөздігім', ru: 'Мой словарь', icon: Bookmark, related: [] },
  { name: 'homework', kk: 'Үй тапсырмасы', ru: 'Домашние задания', icon: ClipboardList, related: [] },
  { name: 'profile', kk: 'Профиль', ru: 'Профиль', icon: UserRound, related: [] },
]
const teacherLinks = [
  { name: 'teacher', kk: 'Шолу', ru: 'Обзор', icon: LayoutDashboard, related: [] },
  { name: 'manage', kk: 'Сабақтарды басқару', ru: 'Управление уроками', icon: PanelTop, related: ['editor'] },
  { name: 'classes', kk: 'Сыныптар', ru: 'Классы', icon: UsersRound, related: [] },
  { name: 'results', kk: 'Нәтижелер', ru: 'Результаты', icon: ChartNoAxesColumnIncreasing, related: [] },
]
const links = computed(() => store.user?.role === 'teacher' ? teacherLinks : studentLinks)
const current = computed(() => links.value.find(link => link.name === route.name || link.related.includes(String(route.name))))
const roleLabel = computed(() => store.user?.role === 'teacher' ? store.t('Мұғалім', 'Учитель') : store.t('Оқушы', 'Ученик'))
watch(() => route.path, () => { mobileOpen.value = false })

async function toggleMenu() {
  mobileOpen.value = !mobileOpen.value
  await nextTick()
  if (mobileOpen.value) firstNav.value?.querySelector<HTMLElement>('a')?.focus()
  else menuToggle.value?.focus()
}
function closeMenu() { if (mobileOpen.value) void toggleMenu() }
function logout() { store.signOut(); void router.replace({ name: 'login' }) }
function reset() {
  dialog.value?.open(store.t('Деректерді қалпына келтіру', 'Сброс демоданных'),
    store.t('Бұл браузердегі өзгерістер жойылып, бастапқы сабақтар мен нәтижелер қалпына келеді.', 'Изменения в этом браузере будут удалены. Восстановятся исходные уроки и результаты.'),
    async () => { await store.reset(); await router.replace({ name: store.user?.role ?? 'login' }) })
}
</script>

<template>
  <div class="app-shell" @keydown.esc="closeMenu">
    <a class="skip-link" href="#main-content" @click.prevent="($event.currentTarget as HTMLElement).ownerDocument.getElementById('main-content')?.focus()">{{ store.t('Мазмұнға өту', 'К содержимому') }}</a>
    <button v-if="mobileOpen" class="nav-scrim" :aria-label="store.t('Мәзірді жабу', 'Закрыть меню')" @click="closeMenu"></button>
    <aside id="app-navigation" class="sidebar" :class="{ 'sidebar-open': mobileOpen }">
      <RouterLink :to="{ name: store.user?.role ?? 'login' }" aria-label="Alaś" class="sidebar-brand"><BrandMark /></RouterLink>
      <div class="sidebar-caption">{{ store.t('ОҚУ КЕҢІСТІГІ', 'УЧЕБНОЕ ПРОСТРАНСТВО') }}</div>
      <nav ref="firstNav" class="side-nav" :aria-label="store.t('Негізгі мәзір', 'Основное меню')">
        <RouterLink v-for="link in links" :key="link.name" :to="{ name: link.name }" :class="{ 'nav-active': current?.name === link.name }" :aria-current="current?.name === link.name ? 'page' : undefined">
          <component :is="link.icon" :size="19" :stroke-width="1.85" /><span>{{ store.t(link.kk, link.ru) }}</span>
        </RouterLink>
      </nav>
      <div class="sidebar-bottom">
        <span class="sidebar-demo"><span></span>{{ store.t('Демо режимі', 'Деморежим') }}</span>
        <button type="button" class="side-action" @click="reset"><RotateCcw :size="17" />{{ store.t('Деректерді ысыру', 'Сбросить данные') }}</button>
        <button type="button" class="side-action" @click="logout"><LogOut :size="17" />{{ store.t('Шығу / рөлді ауыстыру', 'Выйти / сменить роль') }}</button>
      </div>
    </aside>
    <div class="app-body">
      <header class="topbar">
        <div class="topbar-start">
          <button ref="menuToggle" type="button" class="icon-button mobile-menu" :aria-label="store.t('Мәзір', 'Меню')" :aria-expanded="mobileOpen" aria-controls="app-navigation" @click="toggleMenu"><component :is="mobileOpen ? X : Menu" :size="21" /></button>
          <span class="topbar-title">{{ current ? store.t(current.kk, current.ru) : 'Alaś' }}</span>
        </div>
        <div class="topbar-end">
          <LanguageSwitch />
          <div class="top-profile"><span class="avatar">{{ store.user?.initials }}</span><div><strong>{{ store.locale === 'kk' ? store.user?.name : store.user?.nameRu }}</strong><small>{{ roleLabel }}</small></div></div>
        </div>
      </header>
      <main id="main-content" class="main-content" tabindex="-1">
        <p v-if="store.storageError" class="warning-box" role="alert">{{ store.t('Браузер деректерді сақтай алмады. Өзгерістер осы сеанста қолжетімді.', 'Браузер не смог сохранить данные. Изменения доступны в текущем сеансе.') }}</p>
        <slot />
      </main>
      <footer class="app-footer"><span>Alaś education</span><span>{{ store.t('Қазақ тілін үйрену платформасы', 'Платформа для изучения казахского языка') }}</span></footer>
    </div>
    <ConfirmDialog ref="dialog" />
  </div>
</template>
