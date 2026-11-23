<script setup lang="ts">
import { computed, ref } from 'vue'
import { BookMarked, Check, Languages, Minus, Plus } from 'lucide-vue-next'
import { dictionary, splitParagraphs } from '../services/dictionary'
import { usePlatform } from '../stores/platform'
import type { Lesson } from '../types'
import ReadingAudio from './ReadingAudio.vue'
import InteractiveWords from './InteractiveWords.vue'
import WordPopover from './WordPopover.vue'

const props = defineProps<{ lesson: Lesson; preview?: boolean }>()
const emit = defineEmits<{ exercises: [] }>()
const store = usePlatform()
const translated = ref(false)
const font = ref(20)
const reading = computed(() => store.readingPercent(props.lesson))
const paragraphs = computed(() => splitParagraphs(props.lesson.text))
const translations = computed(() => splitParagraphs(dictionary.translation(props.lesson)).filter((_, i) => i % 2 === 0))
const aligned = computed(() => translations.value.length === Math.ceil(paragraphs.value.length / 2))
const popup = ref<InstanceType<typeof WordPopover>>()
function clickWord(token: string, button: HTMLButtonElement, paragraph: number) {
  if (!props.preview) store.recordReading(props.lesson.id, paragraph)
  void popup.value?.open(token, button, dictionary.lookup(props.lesson, token))
}
</script>

<template>
  <section class="card reader">
    <header class="reader-header">
      <div class="section-title"><h2><BookMarked :size="21" /> {{ store.t('Интерактивті мәтін', 'Интерактивный текст') }}</h2></div>
      <div class="reader-controls">
        <div class="font-control" role="group" :aria-label="store.t('Қаріп өлшемі', 'Размер шрифта')">
          <button class="icon-button" :disabled="font <= 16" :aria-label="store.t('Қаріпті кішірейту', 'Уменьшить шрифт')" @click="font -= 2"><Minus :size="17" /></button><span aria-hidden="true">Aa</span><button class="icon-button" :disabled="font >= 32" :aria-label="store.t('Қаріпті үлкейту', 'Увеличить шрифт')" @click="font += 2"><Plus :size="17" /></button>
        </div>
        <button class="button secondary small" :aria-pressed="translated" @click="translated = !translated"><Languages :size="17" />{{ translated ? store.t('Аударманы жасыру', 'Скрыть перевод') : store.t('Орысша аударма', 'Перевод на русский') }}</button>
      </div>
    </header>
    <div v-if="!preview" class="reading-progress"><div><span>{{ store.t('Оқу барысы', 'Прогресс чтения') }}</span><strong>{{ reading }}%</strong></div><progress :value="reading" max="100" :aria-label="store.t('Оқу барысы', 'Прогресс чтения')"></progress></div>
    <ReadingAudio :text="lesson.text" :translation="lesson.translation" />
    <div class="reader-content">
      <p class="reader-hint">{{ store.t('Аудармасын көру үшін мәтіндегі кез келген сөзді басыңыз.', 'Нажмите на любое слово в тексте, чтобы увидеть перевод.') }}</p>
      <div class="reading-copy" :style="{ fontSize: font + 'px' }" lang="kk"><template v-for="(paragraph, index) in paragraphs" :key="index"><span v-if="index % 2">{{ paragraph }}</span><template v-else><InteractiveWords :text="paragraph" :saved="word => !!store.savedWord(lesson.id, { word })" @word="(word, button) => clickWord(word, button, index / 2)" /><span v-if="translated && aligned" class="reader-translation" lang="ru">{{ translations[index / 2] }}</span></template></template></div>
      <p v-if="translated && !aligned" class="reader-translation" lang="ru">{{ dictionary.translation(lesson) || store.t('Аударма қолжетімсіз', 'Перевод недоступен') }}</p>
      <p v-else-if="translated && !lesson.translation && aligned" class="reader-translation">{{ store.t('Аударма қолжетімсіз', 'Перевод недоступен') }}</p>
    </div>
    <footer v-if="!preview" class="reader-footer">
      <button v-if="!store.reading(lesson.id)?.completed" class="button primary" @click="store.recordReading(lesson.id)"><Check :size="18" />{{ store.t('Оқып болдым', 'Чтение завершено') }}</button>
      <span v-else class="badge teal"><Check :size="16" />{{ store.t('Мәтін оқылды', 'Текст прочитан') }}</span>
      <button v-if="lesson.exercises.length" class="button secondary" @click="emit('exercises')">{{ store.t('Жаттығуларға өту', 'К упражнениям') }}</button>
    </footer>
  </section>
  <WordPopover ref="popup" :lesson-id="lesson.id" :preview="preview" />
</template>
