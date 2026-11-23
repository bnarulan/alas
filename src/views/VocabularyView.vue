<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Bookmark, Check, ChevronLeft, ChevronRight, Layers2, RotateCw, Search, Trash2 } from 'lucide-vue-next'
import EmptyState from '../components/EmptyState.vue'
import PronunciationSettings from '../components/PronunciationSettings.vue'
import TTSButton from '../components/TTSButton.vue'
import { normalizeWord } from '../services/dictionary'
import { usePlatform } from '../stores/platform'
const store = usePlatform()
const index = ref(0)
const side = ref(false)
const query = ref('')
const status = ref('all')
const known = computed(() => store.myWords.filter(item => item.status === 'known').length)
const filtered = computed(() => store.myWords.filter(item =>
  (status.value === 'all' || item.status === status.value)
    && normalizeWord(item.entry.word + ' ' + item.entry.translation).includes(normalizeWord(query.value))))
const card = computed(() => filtered.value[index.value])
watch([query, status], () => { index.value = 0; side.value = false })
watch(() => card.value?.id, () => { side.value = false })
watch(() => filtered.value.length, length => { index.value = Math.max(0, Math.min(index.value, length - 1)) })
function move(offset: number) { index.value += offset }
</script>

<template>
  <div class="page-stack">
    <header class="page-heading"><div><h1>{{ store.t('Менің сөздігім', 'Мой словарь') }}</h1><p>{{ store.t('Сақтаған сөздеріңізді карточкалармен қайталаңыз.', 'Повторяйте сохранённые слова с помощью карточек.') }}</p></div><span class="badge teal"><Bookmark :size="16" />{{ store.myWords.length }} {{ store.t('сөз', 'слов') }}</span></header>
    <div class="toolbar"><div class="segments"><button v-for="[key, kk, ru] in [['all', 'Барлығы', 'Все'], ['learning', 'Үйренудемін', 'Изучаю'], ['known', 'Білемін', 'Знаю']]" :key="key" :aria-pressed="status === key" @click="status = key">{{ store.t(kk, ru) }}</button></div><label class="search-field"><Search :size="18" /><input v-model="query" type="search" :aria-label="store.t('Сөз іздеу', 'Поиск слова')" :placeholder="store.t('Сөз іздеу', 'Поиск слова')"></label></div>
    <div v-if="card" class="vocabulary-grid">
      <section class="card panel flash-panel">
        <div class="section-title"><h2><Layers2 :size="21" /> {{ store.t('Карточкалар', 'Карточки') }}</h2><span class="badge slate">{{ index + 1 }} / {{ filtered.length }}</span></div>
        <button class="flashcard" type="button" :class="{ flipped: side }" :aria-pressed="side" @click="side = !side">
          <span>{{ side ? store.t('ОРЫСША', 'ПО-РУССКИ') : store.t('ҚАЗАҚША', 'ПО-КАЗАХСКИ') }}</span><strong :lang="side ? 'ru' : 'kk'">{{ side ? card.entry.translation : card.entry.word }}</strong><small><RotateCw :size="15" />{{ store.t('Аудару үшін басыңыз', 'Нажмите, чтобы перевернуть') }}</small>
        </button>
        <div class="flash-speech">
          <div class="speech-pair">
            <div><TTSButton :text="card.entry.word" language="kk" /><small>{{ store.t('Қазақша', 'Казахский') }}</small></div>
            <div><TTSButton :text="card.entry.translation" language="ru" /><small>{{ store.t('Орысша', 'Русский') }}</small></div>
          </div>
          <PronunciationSettings />
        </div>
        <div class="flash-controls"><button class="icon-button" :disabled="index === 0" :aria-label="store.t('Алдыңғы карточка', 'Предыдущая карточка')" @click="move(-1)"><ChevronLeft :size="21" /></button><button class="button small" :class="card.status === 'known' ? 'secondary' : 'primary'" @click="store.updateWord(card.id, card.status === 'known' ? 'learning' : 'known')"><Check :size="16" />{{ card.status === 'known' ? store.t('Қайта үйрену', 'Повторить снова') : store.t('Білемін', 'Я знаю') }}</button><button class="icon-button" :disabled="index >= filtered.length - 1" :aria-label="store.t('Келесі карточка', 'Следующая карточка')" @click="move(1)"><ChevronRight :size="21" /></button></div>
        <div class="reading-progress"><div><span>{{ store.t('Меңгерілген сөздер', 'Выученные слова') }}</span><strong>{{ known }} / {{ store.myWords.length }}</strong></div><progress :value="known" :max="store.myWords.length || 1" :aria-label="store.t('Меңгерілген сөздер', 'Выученные слова')"></progress></div>
      </section>
      <section class="card panel"><div class="section-title"><h2>{{ store.t('Сақталған сөздер', 'Сохранённые слова') }}</h2></div>
        <div v-for="(item, i) in filtered" :key="item.id" class="vocabulary-row"><button type="button" :aria-pressed="index === i" @click="index = i"><strong lang="kk">{{ item.entry.word }}</strong><small lang="ru">{{ item.entry.translation }}</small></button><span class="badge" :class="item.status === 'known' ? 'teal' : 'slate'">{{ item.status === 'known' ? store.t('Білемін', 'Знаю') : store.t('Үйренудемін', 'Изучаю') }}</span><button type="button" class="icon-button remove-word" :aria-label="store.t('Сөзді өшіру', 'Удалить слово') + ' ' + item.entry.word" @click="store.removeWord(item.id)"><Trash2 :size="16" /></button></div>
      </section>
    </div>
    <div v-else class="card"><EmptyState :title="store.myWords.length ? store.t('Сөз табылмады', 'Слова не найдены') : store.t('Сөздік әзірге бос', 'Словарь пока пуст')" :description="store.t('Мәтіндегі сөзді басып, жеке сөздігіңізге қосыңыз.', 'Нажмите на слово в тексте и добавьте его в словарь.')"><RouterLink class="button primary" :to="{ name: 'catalog' }">{{ store.t('Сабақтарға өту', 'Перейти к урокам') }}</RouterLink></EmptyState></div>
  </div>
</template>
