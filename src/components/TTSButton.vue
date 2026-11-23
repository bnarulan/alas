<script setup lang="ts">
import { computed, onUnmounted, useId, watch } from 'vue'
import { LoaderCircle, Square, Volume2 } from 'lucide-vue-next'
import { playback, pronunciationPreferences, stopSpeech, toggleSpeech } from '../services/pronunciation'
import type { SpeechLanguage, SpeechVoice } from '../services/pronunciation'
import { usePlatform } from '../stores/platform'

const props = defineProps<{ text: string; language: SpeechLanguage; voice?: SpeechVoice; speed?: number; label?: string }>()
const store = usePlatform()
const owner = Symbol()
const statusId = useId()
const state = computed(() => playback.value?.owner === owner ? playback.value : undefined)
const voice = computed(() => props.voice ?? pronunciationPreferences.value.voice)
const speed = computed(() => props.speed ?? pronunciationPreferences.value.speed)
const target = computed(() => props.label ?? (props.language === 'kk'
  ? store.t('Қазақша тыңдау', 'Слушать на казахском')
  : store.t('Орысша тыңдау', 'Слушать на русском')))
const label = computed(() => state.value?.phase === 'playing'
  ? store.t('Дыбыстауды тоқтату', 'Остановить озвучивание') + ' · ' + target.value
  : target.value)
const status = computed(() => {
  if (state.value?.phase === 'loading') return store.t('Дыбыс дайындалып жатыр…', 'Аудио готовится…')
  if (state.value?.phase === 'ready') return store.t('Тыңдау үшін қайта басыңыз.', 'Нажмите ещё раз, чтобы прослушать.')
  switch (state.value?.failure) {
    case 'rate_limited': return store.t('Сұрау тым көп. Сәлден соң қайталаңыз.', 'Слишком много запросов. Повторите чуть позже.')
    case 'invalid_voice': return store.t('Таңдалған дауысқа қолдау көрсетілмейді.', 'Выбранный голос не поддерживается.')
    case 'provider_network_error': return store.t('Дыбыстау қызметіне қосылу мүмкін болмады. Қайталап көріңіз.', 'Не удалось подключиться к сервису озвучивания. Попробуйте ещё раз.')
    case 'synthesis_failed': return store.t('Дыбыстау қызметі аудио дайындай алмады. Қайталап көріңіз.', 'Сервис озвучивания не смог подготовить аудио. Попробуйте ещё раз.')
    case 'internal_error': return store.t('Дыбыстау қызметінде қате шықты. Қайталап көріңіз.', 'Произошла ошибка сервиса озвучивания. Попробуйте ещё раз.')
    case 'timeout': return store.t('Дыбыс дайындалып үлгермеді. Қайталап көріңіз.', 'Аудио не успело загрузиться. Попробуйте ещё раз.')
    case 'text_too_long': return store.t('Тыңдау үшін қысқарақ үзіндіні таңдаңыз.', 'Выберите более короткий отрывок.')
    case 'unavailable': return store.t('Дыбысты ойнату мүмкін болмады. Қайталап көріңіз.', 'Не удалось воспроизвести аудио. Попробуйте ещё раз.')
    default: return ''
  }
})
watch([() => props.text, () => props.language, voice, speed], () => stopSpeech(owner), { flush: 'sync' })
onUnmounted(() => stopSpeech(owner))
function toggle() { toggleSpeech(owner, { text: props.text, language: props.language, voice: voice.value, speed: speed.value }) }
</script>

<template>
  <span class="tts-control">
    <button
      type="button"
      class="icon-button tts-button"
      :data-state="state?.phase ?? 'idle'"
      :aria-label="label"
      :aria-describedby="status ? statusId : undefined"
      :aria-busy="state?.phase === 'loading'"
      :title="label"
      :disabled="!text.trim()"
      :aria-disabled="state?.phase === 'loading' ? true : undefined"
      @click.stop="toggle"
    >
      <LoaderCircle v-if="state?.phase === 'loading'" :size="17" aria-hidden="true" class="tts-spinner" />
      <Square v-else-if="state?.phase === 'playing'" :size="15" aria-hidden="true" />
      <Volume2 v-else :size="18" aria-hidden="true" />
    </button>
    <span :id="statusId" class="tts-status" :class="{ 'sr-only': !status || state?.phase === 'loading' }" role="status">{{ status }}</span>
  </span>
</template>
