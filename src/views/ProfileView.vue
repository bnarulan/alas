<script setup lang="ts">
import { computed } from 'vue'
import { Award, BookOpen, Bookmark, LockKeyhole, Star, Zap } from 'lucide-vue-next'
import { usePlatform } from '../stores/platform'
const store = usePlatform()
const achievements = computed(() => [
  { icon: BookOpen, title: store.t('Алғашқы сабақ', 'Первый урок'), detail: store.t('Бір сабақты толық аяқтаңыз.', 'Завершите один урок.'), unlocked: store.completed >= 1 },
  { icon: Bookmark, title: store.t('Сөз жинаушы', 'Коллекционер слов'), detail: store.t('Сөздікке бес сөз қосыңыз.', 'Сохраните пять слов.'), unlocked: store.myWords.length >= 5 },
  { icon: Star, title: store.t('Үздік нәтиже', 'Отличный результат'), detail: store.t('Елу ұпай жинаңыз.', 'Наберите пятьдесят баллов.'), unlocked: store.points >= 50 },
])
</script>
<template>
  <div class="page-stack">
    <header class="page-heading"><div><h1>{{ store.t('Профиль', 'Профиль') }}</h1><p>{{ store.t('Оқу нәтижелеріңіз бен жетістіктеріңіз.', 'Ваши результаты и достижения.') }}</p></div></header>
    <section class="card panel profile-card">
      <span class="avatar avatar-large">{{ store.user?.initials }}</span>
      <div><h2>{{ store.locale === 'kk' ? store.user?.name : store.user?.nameRu }}</h2><p class="muted">{{ store.t('Демо оқушы', 'Демоученик') }}</p></div>
      <span class="badge orange"><Zap :size="16" /> {{ store.points }} {{ store.t('ұпай', 'баллов') }}</span>
    </section>
    <section><div class="section-title"><h2>{{ store.t('Жетістіктер', 'Достижения') }}</h2></div>
      <div class="lesson-grid"><article v-for="achievement in achievements" :key="achievement.title" class="card panel achievement-card">
        <span class="icon-tile" :class="achievement.unlocked ? 'orange' : 'slate'"><component :is="achievement.unlocked ? achievement.icon : LockKeyhole" :size="24" /></span>
        <h3>{{ achievement.title }}</h3><p>{{ achievement.detail }}</p><span class="badge" :class="achievement.unlocked ? 'teal' : 'slate'"><Award :size="14" />{{ achievement.unlocked ? store.t('Алынды', 'Получено') : store.t('Әзірге ашылмады', 'Пока закрыто') }}</span>
      </article></div>
    </section>
  </div>
</template>
