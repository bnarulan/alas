<script setup lang="ts">
import { BookOpen, Check, Clock3, Files, MapPin, MessageCircle } from 'lucide-vue-next'
import { computed } from 'vue'
import { usePlatform } from '../stores/platform'
import { subjectLabel } from '../format'
import type { Lesson } from '../types'
const props = defineProps<{ lesson: Lesson }>()
const store = usePlatform()
const progress = computed(() => store.lessonProgress(props.lesson))
const icons = { teal: Files, violet: MessageCircle, blue: MapPin }
</script>
<template>
  <RouterLink class="lesson-card card" :to="{ name: 'lesson', params: { id: lesson.id } }">
    <div class="lesson-art" :class="lesson.theme"><span class="lesson-orbit"></span><span class="lesson-art-icon"><component :is="icons[lesson.theme] || BookOpen" :size="28" :stroke-width="1.65" /></span><span v-if="progress === 100" class="lesson-check"><Check :size="16" /></span></div>
    <div class="lesson-body">
      <div class="lesson-meta"><span>{{ subjectLabel(lesson, store.locale) }}</span><span><Clock3 :size="13" /> {{ lesson.minutes }} {{ store.t('мин', 'мин') }}</span></div>
      <h3>{{ lesson.title }}</h3><p>{{ lesson.description }}</p>
      <div class="lesson-state"><span :class="{ 'completed-text': progress === 100 }">{{ progress === 100 ? store.t('Аяқталды', 'Пройдено') : progress || store.readingPercent(lesson) ? store.t('Жалғасуда', 'В процессе') : store.t('Бастау', 'Начать') }}</span><span v-if="progress" class="muted">{{ progress }}%</span></div>
    </div>
  </RouterLink>
</template>
