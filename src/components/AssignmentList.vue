<script setup lang="ts">
import { CalendarDays, Check, ClipboardList } from 'lucide-vue-next'
import { dateLabel } from '../format'
import { usePlatform } from '../stores/platform'
import type { Assignment } from '../types'
import EmptyState from './EmptyState.vue'
defineProps<{ assignments: Assignment[] }>()
const store = usePlatform()
const getLesson = (id: string) => store.catalog.find(item => item.id === id)
const isDone = (id: string) => { const lesson = getLesson(id); return lesson && store.lessonProgress(lesson) === 100 }
</script>
<template>
  <div v-if="assignments.length" class="assignment-list">
    <RouterLink v-for="assignment in assignments" :key="assignment.id" class="assignment-row" :to="{ name: 'lesson', params: { id: assignment.lessonId } }">
      <span class="icon-tile" :class="isDone(assignment.lessonId) ? 'teal' : 'orange'"><component :is="isDone(assignment.lessonId) ? Check : ClipboardList" :size="19" /></span>
      <span class="row-copy"><strong>{{ getLesson(assignment.lessonId)?.title }}</strong><small><CalendarDays :size="13" /> {{ store.t('Мерзімі', 'Срок') }} · {{ dateLabel(assignment.due, store.locale) }}</small></span>
      <span class="badge" :class="isDone(assignment.lessonId) ? 'teal' : 'orange'">{{ isDone(assignment.lessonId) ? store.t('Орындалды', 'Выполнено') : store.t('Тапсырылды', 'Назначено') }}</span>
    </RouterLink>
  </div>
  <EmptyState v-else :title="store.t('Әзірге тапсырма жоқ', 'Заданий пока нет')" :description="store.t('Мұғалім тағайындаған сабақтар осы жерде көрінеді.', 'Здесь появятся уроки, назначенные учителем.')" />
</template>
