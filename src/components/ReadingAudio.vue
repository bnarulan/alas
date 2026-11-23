<script setup lang="ts">
import { computed, ref } from 'vue'
import { Headphones } from 'lucide-vue-next'
import { splitParagraphs } from '../services/dictionary'
import { sentences } from '../services/pronunciation'
import type { SpeechLanguage } from '../services/pronunciation'
import { usePlatform } from '../stores/platform'
import PronunciationSettings from './PronunciationSettings.vue'
import TTSButton from './TTSButton.vue'

const props = defineProps<{ text: string; translation: string }>()
const store = usePlatform()
const language = ref<SpeechLanguage>('kk')
const selection = ref('full')
const source = computed(() => language.value === 'ru' ? props.translation : props.text)
const paragraphs = computed(() => splitParagraphs(source.value).filter((part, index) => index % 2 === 0 && part.trim()))
const sections = computed(() => paragraphs.value.flatMap(part => sentences(part, language.value).map(text => text.trim()).filter(Boolean)))
const selectedText = computed(() => {
  if (selection.value === 'full') return source.value
  const [type, index] = selection.value.split(':')
  return (type === 'paragraph' ? paragraphs.value : sections.value)[Number(index)] ?? source.value
})

function preview(text: string) {
  const short = Array.from(text.trim()).slice(0, 54).join('')
  return short.length < text.trim().length ? short + '…' : short
}
</script>

<template>
  <div v-if="text.trim()" class="reading-audio">
    <div class="reading-audio-controls">
      <span class="reading-audio-title"><Headphones :size="17" />{{ store.t('Мәтінді тыңдау', 'Слушать текст') }}</span>
      <div class="reading-audio-picker">
        <label v-if="translation.trim()" class="field speech-language">
          <span class="sr-only">{{ store.t('Дыбыстау тілі', 'Язык озвучивания') }}</span>
          <select v-model="language" @change="selection = 'full'"><option value="kk">{{ store.t('Қазақша', 'Казахский') }}</option><option value="ru">{{ store.t('Орысша', 'Русский') }}</option></select>
        </label>
        <label class="field speech-section">
          <span class="sr-only">{{ store.t('Тыңдайтын үзінді', 'Отрывок для прослушивания') }}</span>
          <select v-model="selection">
            <option value="full">{{ store.t('Толық мәтін', 'Весь текст') }}</option>
            <optgroup v-if="paragraphs.length > 1" :label="store.t('Абзацтар', 'Абзацы')">
              <option v-for="(item, index) in paragraphs" :key="index" :value="'paragraph:' + index">{{ index + 1 }} · {{ preview(item) }}</option>
            </optgroup>
            <optgroup v-if="sections.length > 1" :label="store.t('Сөйлемдер', 'Предложения')">
              <option v-for="(item, index) in sections" :key="index" :value="'sentence:' + index">{{ index + 1 }} · {{ preview(item) }}</option>
            </optgroup>
          </select>
        </label>
        <TTSButton :text="selectedText" :language="language" :label="store.t('Үзіндіні тыңдау', 'Прослушать отрывок')" />
      </div>
    </div>
    <PronunciationSettings />
  </div>
</template>
