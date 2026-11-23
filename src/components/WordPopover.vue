<script setup lang="ts">
import { computed, nextTick, ref, useId, watch } from 'vue'
import { Bookmark, Check, X } from 'lucide-vue-next'
import { wordSpeechText } from '../services/pronunciation'
import { usePlatform } from '../stores/platform'
import type { Word } from '../types'
import TTSButton from './TTSButton.vue'

const props = defineProps<{ lessonId: string; preview?: boolean }>()
const store = usePlatform()
const openWord = ref<{ token: string; entry?: Word; button: HTMLButtonElement }>()
const titleId = useId()
const popup = ref<HTMLElement>()
const dismiss = ref<HTMLButtonElement>()
const position = ref({ top: 0, left: 0 })
const saved = computed(() => openWord.value?.entry && store.savedWord(props.lessonId, openWord.value.entry))
watch(popup, (element, _, onCleanup) => {
  if (!element) return
  const observer = new ResizeObserver(relocate)
  observer.observe(element)
  onCleanup(() => observer.disconnect())
})
function relocate() {
  if (!openWord.value || !popup.value) return
  if (!openWord.value.button.isConnected) { close(); return }
  const anchor = openWord.value.button.getBoundingClientRect()
  const { offsetWidth: width, offsetHeight: height } = popup.value
  position.value = {
    left: Math.max(12, Math.min(anchor.left, window.innerWidth - width - 12)),
    top: Math.max(12, Math.min(anchor.bottom + 9 + height < window.innerHeight ? anchor.bottom + 9 : anchor.top - height - 9, window.innerHeight - height - 12)),
  }
}
async function open(token: string, button: HTMLButtonElement, entry?: Word) {
  if (button === openWord.value?.button) { close(true); return }
  openWord.value = { token, entry, button }
  await nextTick()
  relocate()
  dismiss.value?.focus({ preventScroll: true })
}
defineExpose({ open, close })
function close(focus = false) {
  const anchor = openWord.value?.button
  openWord.value = undefined
  if (focus) anchor?.focus({ preventScroll: true })
}
function outside(event: PointerEvent) {
  const target = event.target as Node
  if (!popup.value?.contains(target) && !openWord.value?.button.contains(target)) close()
}
function keydown(event: KeyboardEvent) {
  if (!openWord.value) return
  if (event.key === 'Escape') { event.preventDefault(); close(true) }
  if (event.key === 'Tab' && popup.value?.contains(document.activeElement)) {
    const buttons = [...popup.value.querySelectorAll('button:not(:disabled)')]
    const boundary = event.shiftKey ? buttons[0] : buttons.at(-1)
    if (document.activeElement === boundary) {
      close(true)
    }
  }
}
async function toggleSave() {
  if (!openWord.value?.entry || props.preview) return
  store.toggleWord(props.lessonId, openWord.value.entry)
  await nextTick()
  relocate()
}
watch(openWord, (word, _, onCleanup) => {
  if (!word) return
  document.addEventListener('pointerdown', outside)
  document.addEventListener('keydown', keydown)
  window.addEventListener('resize', relocate)
  window.addEventListener('scroll', relocate, { passive: true })
  onCleanup(() => {
    document.removeEventListener('pointerdown', outside)
    document.removeEventListener('keydown', keydown)
    window.removeEventListener('resize', relocate)
    window.removeEventListener('scroll', relocate)
  })
})
</script>

<template>
  <Teleport to="body">
    <section v-if="openWord" ref="popup" class="word-popover" role="dialog" :aria-labelledby="titleId" :style="{ top: position.top + 'px', left: position.left + 'px' }">
      <header><span class="badge teal">{{ store.t('Сөздік', 'Словарь') }}</span><button ref="dismiss" class="icon-button" :aria-label="store.t('Жабу', 'Закрыть')" @click="close(true)"><X :size="18" /></button></header>
      <div class="word-audio-line">
        <h3 :id="titleId" lang="kk">{{ openWord.token }}</h3>
        <TTSButton :text="wordSpeechText(openWord.token)" language="kk" />
      </div>
      <template v-if="openWord.entry">
        <div class="word-audio-line">
          <p class="word-translation" lang="ru">{{ openWord.entry.translation }}</p>
          <TTSButton :text="openWord.entry.translation" language="ru" />
        </div>
        <p v-if="openWord.entry.lemma" class="word-lemma">{{ store.t('Сөздің түбір тұлғасы', 'Словарная форма') }} · <strong lang="kk">{{ openWord.entry.lemma }}</strong></p>
        <p v-if="openWord.entry.explanation" class="word-explanation" lang="kk">{{ openWord.entry.explanation }}</p>
        <blockquote v-if="openWord.entry.example" lang="kk">{{ openWord.entry.example }}</blockquote>
        <button v-if="!preview" class="button small" :class="saved ? 'secondary' : 'primary'" :aria-pressed="!!saved" @click="toggleSave"><component :is="saved ? Check : Bookmark" :size="17" />{{ saved ? store.t('Сөздікте сақталған', 'Сохранено в словаре') : store.t('Сөздікке қосу', 'Добавить в словарь') }}</button>
      </template>
      <p v-else class="muted">{{ store.t('Аударма қолжетімсіз', 'Перевод недоступен') }}</p>
    </section>
  </Teleport>
</template>
