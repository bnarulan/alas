<script setup lang="ts">
import { computed } from 'vue'
import { Activity, BookOpen, ClipboardCheck, Plus, UsersRound } from 'lucide-vue-next'
import EmptyState from '../components/EmptyState.vue'
import { averageScore, attemptsFor } from '../services/analytics'
import { usePlatform } from '../stores/platform'
const store = usePlatform()
const recent = computed(() => [...store.data.submissions].sort((a, b) => b.createdAt - a.createdAt).slice(0, 4))
const groupStats = computed(() => store.data.classes.map(group => ({
  group, average: averageScore(attemptsFor(store.data.submissions, group.studentIds)),
})))
const name = computed(() => (store.locale === 'kk' ? store.user?.name : store.user?.nameRu)?.split(' ')[0])
const cards = computed(() => [
  { icon: UsersRound, value: store.data.classes.length, label: store.t('Сыныптар', 'Классы'), theme: 'blue', route: 'classes' },
  { icon: BookOpen, value: store.catalog.length, label: store.t('Жарияланған сабақтар', 'Опубликованные уроки'), theme: 'teal', route: 'manage' },
  { icon: ClipboardCheck, value: store.data.submissions.length, label: store.t('Жаттығу жауаптары', 'Ответы на упражнения'), theme: 'violet', route: 'results' },
])
</script>
<template>
  <div class="page-stack">
    <header class="page-heading"><div><h1>{{ store.t('Сәлеметсіз бе', 'Здравствуйте') }}, {{ name }}!</h1><p>{{ store.t('Сыныптарыңыз, сабақтарыңыз және оқу нәтижелері бір жерде.', 'Ваши классы, уроки и результаты обучения в одном месте.') }}</p></div><RouterLink class="button primary" :to="{ name: 'editor' }"><Plus :size="18" />{{ store.t('Жаңа сабақ', 'Новый урок') }}</RouterLink></header>
    <div class="stat-grid"><RouterLink v-for="card in cards" :key="card.route" :to="{ name: card.route }" class="card teacher-stat"><span class="icon-tile" :class="card.theme"><component :is="card.icon" :size="23" /></span><div><strong>{{ card.value }}</strong><span>{{ card.label }}</span></div></RouterLink></div>
    <div class="teacher-grid">
      <section class="card panel"><div class="section-title"><h2><Activity :size="21" />{{ store.t('Сынып нәтижелері', 'Результаты классов') }}</h2><RouterLink class="text-link" :to="{ name: 'classes' }">{{ store.t('Сыныптар', 'Классы') }}</RouterLink></div>
        <p v-if="groupStats.length" class="muted section-detail">{{ store.t('Әр сыныптағы оқушылардың соңғы жауаптарының дәлдігі.', 'Точность последних ответов учеников каждого класса.') }}</p>
        <div v-if="groupStats.length" class="chart-bars"><div v-for="{ group, average } in groupStats" :key="group.id"><div><strong>{{ group.name }}</strong><span>{{ average === null ? store.t('Нәтиже жоқ', 'Нет ответов') : average + '%' }}</span></div><progress :value="average ?? 0" max="100" :aria-label="group.name"></progress></div></div>
        <EmptyState v-else :title="store.t('Сыныптар әзірге жоқ', 'Классов пока нет')" />
      </section>
      <section class="card panel"><div class="section-title"><h2>{{ store.t('Соңғы жауаптар', 'Последние ответы') }}</h2><RouterLink class="text-link" :to="{ name: 'results' }">{{ store.t('Барлығы', 'Все') }}</RouterLink></div>
        <div v-if="recent.length" class="teacher-recent"><RouterLink v-for="result in recent" :key="result.id" :to="{ name: 'results', query: { student: result.userId } }"><span class="icon-tile teal"><ClipboardCheck :size="18" /></span><span class="row-copy"><strong>{{ store.data.lessons.find(lesson => lesson.id === result.lessonId)?.title }}</strong><small>{{ store.data.users.find(user => user.id === result.userId)?.[store.locale === 'kk' ? 'name' : 'nameRu'] }}</small></span><span class="badge slate">{{ result.score }}/{{ result.possible }}</span></RouterLink></div>
        <EmptyState v-else :title="store.t('Жауаптар әзірге жоқ', 'Пока ответов нет')" />
      </section>
    </div>
  </div>
</template>
