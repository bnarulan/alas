<script setup lang="ts">
import { computed, ref } from 'vue'
import { BookOpen, Search } from 'lucide-vue-next'
import LessonCard from '../components/LessonCard.vue'
import EmptyState from '../components/EmptyState.vue'
import { usePlatform } from '../stores/platform'
import { normalizeWord } from '../services/dictionary'
import { subjectLabel } from '../format'
const store = usePlatform()
const query = ref('')
const filter = ref('all')
const course = ref('')
const courses = computed(() => [...new Set(store.catalog.map(lesson => lesson.subject))].map(subject => ({
  subject, representative: store.catalog.find(lesson => lesson.subject === subject)!,
  count: store.catalog.filter(lesson => lesson.subject === subject).length,
})))
const filters = [['all', 'Барлығы', 'Все'], ['current', 'Аяқталмаған', 'В процессе'], ['finished', 'Аяқталған', 'Пройденные']]
const lessons = computed(() => store.catalog.filter(lesson => {
  const completed = store.lessonProgress(lesson) === 100
  return normalizeWord(lesson.title + ' ' + lesson.subject).includes(normalizeWord(query.value))
    && (!course.value || lesson.subject === course.value)
    && (filter.value === 'all' || completed === (filter.value === 'finished'))
}))
</script>
<template>
  <div class="page-stack">
    <header class="page-heading"><div><h1>{{ store.t('Сабақтар', 'Уроки') }}</h1><p>{{ store.t('Мәтіндер, сөздік және жаттығулар арқылы қазақ тілін меңгеріңіз.', 'Изучайте казахский язык с текстами, словарём и упражнениями.') }}</p></div></header>
    <section v-if="courses.length" class="card panel course-panel">
      <div class="section-title"><h2><BookOpen :size="19" />{{ store.t('Оқу курстары', 'Учебные курсы') }}</h2></div>
      <div class="course-options" role="group" :aria-label="store.t('Курсты таңдау', 'Выбор курса')">
        <button v-if="courses.length > 1" class="button secondary small" :aria-pressed="!course" @click="course = ''">{{ store.t('Барлық курс', 'Все курсы') }}</button>
        <template v-for="item in courses" :key="item.subject">
          <button v-if="courses.length > 1" class="button secondary small" :aria-pressed="course === item.subject" @click="course = item.subject">{{ subjectLabel(item.representative, store.locale) }} <span class="badge teal">{{ item.count }}</span></button>
          <span v-else class="badge teal">{{ subjectLabel(item.representative, store.locale) }} · {{ item.count }} {{ store.t('сабақ', 'уроков') }}</span>
        </template>
      </div>
    </section>
    <div class="toolbar">
      <div class="segments"><button v-for="[key, kk, ru] in filters" :key="key" :aria-pressed="filter === key" @click="filter = key">{{ store.t(kk, ru) }}</button></div>
      <label class="search-field"><Search :size="18" /><input v-model="query" type="search" :aria-label="store.t('Сабақ іздеу', 'Поиск урока')" :placeholder="store.t('Сабақ іздеу', 'Поиск урока')"></label>
    </div>
    <div v-if="lessons.length" class="lesson-grid"><LessonCard v-for="lesson in lessons" :key="lesson.id" :lesson="lesson" /></div>
    <div v-else class="card"><EmptyState :title="store.t('Сабақ табылмады', 'Уроки не найдены')" :description="store.t('Іздеу сөзін немесе сүзгіні өзгертіп көріңіз.', 'Попробуйте изменить запрос или фильтр.')" /></div>
  </div>
</template>
