<script setup lang="ts">
import { computed, inject } from 'vue'
import type { Word } from '../types'
import { exerciseLanguage } from '../services/exercise-translation'
import InteractiveWords from './InteractiveWords.vue'

const props = defineProps<{ text: string; ru?: string; context?: string; entry?: Word; wordsOnly?: boolean; missing?: boolean }>()
const language = inject(exerciseLanguage)!
const translation = computed(() => props.wordsOnly ? undefined : language.translation(props.text, props.ru))
const unavailable = computed(() => props.missing && language.visible() && !props.wordsOnly && !translation.value)
</script>

<template>
  <span class="exercise-text"><InteractiveWords :text="text" :saved="language.saved" @word="(word, button) => language.openWord(context ?? text, word, button, entry)" /><span v-if="translation" class="exercise-translation" lang="ru">{{ translation }}</span><span v-else-if="unavailable" class="exercise-translation" lang="ru">Перевод недоступен</span></span>
</template>
