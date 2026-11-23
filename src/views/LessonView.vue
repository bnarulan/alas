<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { BookOpen, Check, Clock3, Dumbbell } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import InteractiveReader from '../components/InteractiveReader.vue'
import ExercisePlayer from '../components/ExercisePlayer.vue'
import EmptyState from '../components/EmptyState.vue'
import { subjectLabel } from '../format'
import { usePlatform } from '../stores/platform'

const store = usePlatform()
const route = useRoute()
const router = useRouter()
const lesson = computed(() => store.catalog.find(item => item.id === route.params.id))
const tab = computed(() => route.query.tab === 'practice' ? 'practice' : 'reading')
const practiceTab = ref<HTMLButtonElement>()
const readingTab = ref<HTMLButtonElement>()
async function setTab(value: string, focus = false) {
  await router.replace({ query: value === 'practice' ? { tab: 'practice' } : {} })
  if (focus) { await nextTick(); (value === 'practice' ? practiceTab.value : readingTab.value)?.focus() }
}
watch(() => lesson.value?.id, () => window.scrollTo(0, 0))
</script>
<template>
  <div v-if="lesson" class="page-stack lesson-view">
    <RouterLink class="text-link back-link" :to="{ name: 'catalog' }">{{ store.t('Барлық сабақтар', 'Все уроки') }}</RouterLink>
    <header class="page-heading"><div><div class="lesson-heading-meta"><span class="badge teal">{{ subjectLabel(lesson, store.locale) }}</span><span class="muted">{{ lesson.grade }} {{ store.t('сынып', 'класс') }}</span><span class="muted"><Clock3 :size="15" /> {{ lesson.minutes }} {{ store.t('мин', 'мин') }}</span></div><h1 lang="kk">{{ lesson.title }}</h1><p lang="kk">{{ lesson.description }}</p></div><span v-if="store.lessonProgress(lesson) === 100" class="badge teal"><Check :size="16" />{{ store.t('Аяқталды', 'Пройдено') }}</span></header>
    <div class="lesson-tabs" role="group" :aria-label="store.t('Сабақ бөлімдері', 'Разделы урока')">
      <button ref="readingTab" type="button" :aria-pressed="tab === 'reading'" @click="setTab('reading')"><BookOpen :size="18" /> {{ store.t('Мәтін оқу', 'Чтение') }}</button>
      <button ref="practiceTab" type="button" :aria-pressed="tab === 'practice'" @click="setTab('practice')"><Dumbbell :size="18" /> {{ store.t('Жаттығулар', 'Упражнения') }} <span>{{ lesson.exercises.length }}</span></button>
    </div>
    <InteractiveReader v-if="tab === 'reading'" :lesson="lesson" @exercises="setTab('practice', true)" />
    <section v-else class="practice-stack">
      <div class="section-title"><h2>{{ store.t('Біліміңізді бекітіңіз', 'Закрепите знания') }}</h2><span class="badge slate">{{ lesson.exercises.filter(ex => store.latestResult(lesson!.id, ex.id)).length }} / {{ lesson.exercises.length }}</span></div>
      <ExercisePlayer v-for="(exercise, index) in lesson.exercises" :key="exercise.id" :exercise="exercise" :lesson="lesson" :number="index + 1" />
      <div v-if="!lesson.exercises.length" class="card"><EmptyState :title="store.t('Жаттығу әзірге жоқ', 'Упражнений пока нет')" /></div>
    </section>
  </div>
  <div v-else class="card"><EmptyState :title="store.t('Сабақ қолжетімсіз', 'Урок недоступен')"><RouterLink class="button primary" :to="{ name: 'catalog' }">{{ store.t('Сабақтар тізімі', 'Список уроков') }}</RouterLink></EmptyState></div>
</template>
