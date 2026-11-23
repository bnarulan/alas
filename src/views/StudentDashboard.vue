<script setup lang="ts">
import { computed } from 'vue'
import { Award, BookOpen, Bookmark, ChevronRight, Clock3, Sparkles, Zap } from 'lucide-vue-next'
import AssignmentList from '../components/AssignmentList.vue'
import LessonCard from '../components/LessonCard.vue'
import EmptyState from '../components/EmptyState.vue'
import { usePlatform } from '../stores/platform'
import { subjectLabel } from '../format'

const store = usePlatform()
const available = computed(() => store.catalog.filter(lesson => store.lessonProgress(lesson) < 100))
const nextLesson = computed(() => [...available.value].sort((a, b) =>
  (store.reading(b.id)?.updatedAt ?? 0) - (store.reading(a.id)?.updatedAt ?? 0))[0] ?? store.catalog[0])
const progress = computed(() => store.catalog.length ? Math.round(store.catalog.reduce((sum, lesson) => sum + store.lessonProgress(lesson), 0) / store.catalog.length) : 0)
const name = computed(() => (store.locale === 'kk' ? store.user?.name : store.user?.nameRu)?.split(' ')[0])
</script>

<template>
  <div class="page-stack">
    <header class="page-heading dashboard-heading"><div><h1>{{ store.t('Сәлем', 'Привет') }}, {{ name }}! <span class="heading-sparkle" aria-hidden="true">✦</span></h1><p>{{ store.t('Бүгін қазақ тілін бірге үйренейік.', 'Продолжим изучать казахский язык сегодня.') }}</p></div></header>
    <div class="dashboard-grid">
      <section v-if="nextLesson" class="study-hero">
        <div class="study-hero-copy"><span class="hero-kicker"><BookOpen :size="16" /> {{ store.t('ОҚУДЫ ЖАЛҒАСТЫРУ', 'ПРОДОЛЖИТЬ ОБУЧЕНИЕ') }}</span>
          <h2>{{ nextLesson.title }}</h2><p>{{ nextLesson.description }}</p>
          <div class="hero-meta"><span>{{ subjectLabel(nextLesson, store.locale) }}</span><span><Clock3 :size="14" /> {{ nextLesson.minutes }} {{ store.t('мин', 'мин') }}</span></div>
          <RouterLink class="button hero-button" :to="{ name: 'lesson', params: { id: nextLesson.id } }">{{ !available.length ? store.t('Сабақты қайталау', 'Повторить урок') : store.t('Сабақты жалғастыру', 'Продолжить урок') }}</RouterLink>
        </div>
      </section>
      <div v-else class="card"><EmptyState :title="store.t('Сабақтар әзірге жоқ', 'Уроков пока нет')" /></div>
      <section class="card progress-card">
        <div class="section-title"><h2>{{ store.t('Менің ілгерілеуім', 'Мой прогресс') }}</h2><span class="icon-tile teal"><Sparkles :size="17" /></span></div>
        <div class="progress-overview"><div class="progress-ring" :style="{ '--percent': progress + '%' }"><span>{{ progress }}%</span></div><div><strong>{{ store.t('Оқу барысы', 'Прогресс обучения') }}</strong><small>{{ store.completed }} / {{ store.catalog.length }} {{ store.t('сабақ аяқталды', 'уроков пройдено') }}</small></div></div>
        <div class="progress-stats"><div><Zap :size="18" class="amber-text" /><strong>{{ store.points }}</strong><small>{{ store.t('ұпай', 'баллов') }}</small></div><div><Bookmark :size="17" class="teal-text" /><strong>{{ store.myWords.length }}</strong><small>{{ store.t('сөз', 'слов') }}</small></div></div>
      </section>
    </div>
    <div class="dashboard-grid second-grid">
      <section>
        <div class="section-title"><h2>{{ store.t('Сабақтар', 'Уроки') }}</h2><RouterLink class="text-link" :to="{ name: 'catalog' }">{{ store.t('Барлығын көру', 'Смотреть все') }} <ChevronRight :size="16" /></RouterLink></div>
        <div v-if="store.catalog.length" class="lesson-grid dashboard-lessons"><LessonCard v-for="lesson in store.catalog.slice(0, 3)" :key="lesson.id" :lesson="lesson" /></div>
        <div v-else class="card"><EmptyState :title="store.t('Сабақтар әзірге жоқ', 'Уроков пока нет')" /></div>
      </section>
      <div class="dashboard-aside">
        <section class="card widget"><div class="section-title"><h2>{{ store.t('Үй тапсырмасы', 'Домашнее задание') }}</h2></div><AssignmentList :assignments="store.myAssignments.slice(0, 2)" /></section>
        <section class="card widget word-widget"><div class="section-title"><h2>{{ store.t('Соңғы сөздер', 'Недавние слова') }}</h2><RouterLink class="icon-button" :to="{ name: 'vocabulary' }" :aria-label="store.t('Сөздікті ашу', 'Открыть словарь')"><ChevronRight :size="17" /></RouterLink></div>
          <div v-if="store.myWords.length" class="recent-words"><div v-for="item in store.myWords.slice(0, 3)" :key="item.id"><strong>{{ item.entry.word }}</strong><span lang="ru">{{ item.entry.translation }}</span></div></div>
          <p v-else class="muted">{{ store.t('Оқу кезінде сақтаған сөздер осында шығады.', 'Здесь появятся слова, сохранённые при чтении.') }}</p>
        </section>
      </div>
    </div>
    <RouterLink class="card achievement-strip" :to="{ name: 'profile' }"><span class="icon-tile orange"><Award :size="24" /></span><div><strong>{{ store.t('Жетістіктерім', 'Мои достижения') }}</strong><small>{{ store.t('Оқу нәтижелері мен марапаттарды қараңыз.', 'Посмотрите результаты и награды за обучение.') }}</small></div><ChevronRight :size="19" /></RouterLink>
  </div>
</template>
