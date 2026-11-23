<script setup lang="ts">
import { computed, ref, toRaw } from 'vue'
import { BookOpen, Dumbbell, Eye, Plus, Save, Trash2 } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import EmptyState from '../components/EmptyState.vue'
import ExerciseBuilder from '../components/ExerciseBuilder.vue'
import InteractiveReader from '../components/InteractiveReader.vue'
import { normalizeWord, tokenize } from '../services/dictionary'
import { newId } from '../services/identifiers'
import { usePlatform } from '../stores/platform'
import type { Exercise, Lesson } from '../types'

const store = usePlatform()
const route = useRoute()
const router = useRouter()
const existing = store.data.lessons.find(item => item.id === route.params.id)
const draft = ref<Lesson>(existing ? structuredClone(toRaw(existing)) : {
  id: newId(), title: '', subject: 'Қазақ тілі', grade: 9, description: '', text: '', translation: '',
  vocabulary: [], exercises: [], published: true, theme: 'teal', minutes: 10,
})
const missing = computed(() => !!route.params.id && !existing)
const preview = ref(false)
const error = ref('')
const wordTokens = computed(() => new Set(tokenize(draft.value.text).filter(token => token.isWord).map(token => normalizeWord(token.value))))
function addWord() { draft.value.vocabulary.push({ word: '', lemma: '', translation: '', explanation: '', example: '' }) }
function addExercise() { draft.value.exercises.push({ type: 'choice', id: newId(), prompt: '', options: ['', ''], optionIds: [newId(), newId()], answer: 0 }) }
function scoredContent({ translation: _translation, hint: _hint, explanation: _explanation, ...item }: Exercise) {
  return JSON.stringify(item)
}
function validExercise(item: Exercise) {
  if (!item.prompt) return false
  switch (item.type) {
    case 'multiple-selection': return item.options.some(option => option.formal)
    case 'inline-blanks': return item.questions.length > 0 && item.questions.every(question => question.answers.length > 0 && question.parts.length === question.answers.length + 1 && question.answers.every(Boolean))
    case 'choice': return item.options.length >= 2 && item.options.every(Boolean) && new Set(item.options.map(normalizeWord)).size === item.options.length
    case 'order': return item.words.length >= 2 && new Set(item.words.map(normalizeWord)).size > 1
    case 'fill': return item.answers.length > 0 && item.answers.every(Boolean)
    case 'match': return item.pairs.length >= 2 && item.pairs.every(pair => pair.word && pair.translation)
      && new Set(item.pairs.map(pair => normalizeWord(pair.word))).size === item.pairs.length
    case 'review': return item.cards.length > 0 && item.cards.every(card => card.word && card.translation)
    case 'boolean': return true
  }
}
function save() {
  const value = structuredClone(toRaw(draft.value))
  if (!value.title || !value.subject || !value.text.trim()) {
    error.value = store.t('Атауды, пәнді және мәтінді толтырыңыз.', 'Укажите название, предмет и текст.')
    return
  }
  const keys = value.vocabulary.map(entry => normalizeWord(entry.word))
  if (keys.some(key => !wordTokens.value.has(key)) || new Set(keys).size !== keys.length) {
    error.value = store.t('Сөздікке мәтінде кездесетін сөз тұлғаларын қайталамай енгізіңіз.', 'Добавьте в словарь уникальные формы слов, которые встречаются в тексте.')
    return
  }
  if (!value.exercises.every(validExercise)) {
    error.value = store.t('Жаттығулардың барлық өрістерін тексеріңіз. Сөйлемде кемінде екі түрлі сөз, ал таңдау жаттығуында қайталанбайтын жауаптар болуы керек.', 'Проверьте поля упражнений. В предложении должно быть два разных слова, а варианты ответа должны быть уникальными.')
    return
  }
  value.exercises = value.exercises.map(item => {
    const old = existing?.exercises.find(candidate => candidate.id === item.id)
    return old && scoredContent(old) !== scoredContent(item) ? { ...item, id: newId() } : item
  })
  store.saveLesson(value)
  void router.push({ name: 'manage', query: { saved: value.id } })
}
</script>

<template>
  <div v-if="!missing" class="page-stack editor-view">
    <RouterLink class="text-link back-link" :to="{ name: 'manage' }">{{ store.t('Сабақтарды басқару', 'Управление уроками') }}</RouterLink>
    <header class="page-heading"><div><h1>{{ existing ? store.t('Сабақты өңдеу', 'Редактировать урок') : store.t('Жаңа сабақ', 'Новый урок') }}</h1><p>{{ store.t('Мәтін, сөздік және жаттығуларды бір сабаққа біріктіріңіз.', 'Объедините текст, словарь и упражнения в одном уроке.') }}</p></div></header>
    <form class="page-stack" @submit.prevent="save">
      <section class="card panel form-section">
        <div class="section-title"><h2>{{ store.t('Сабақ туралы', 'Об уроке') }}</h2></div>
        <label class="field">{{ store.t('Сабақ атауы', 'Название урока') }}<input v-model.trim="draft.title" required maxlength="100" :placeholder="store.t('Мысалы, Менің мектебім', 'Например, Моя школа')"></label>
        <div class="form-grid cols-three">
          <label class="field">{{ store.t('Пән', 'Предмет') }}<input v-model.trim="draft.subject" required maxlength="60"></label>
          <label class="field">{{ store.t('Сынып', 'Класс') }}<input v-model.number="draft.grade" type="number" min="1" max="12" required></label>
          <label class="field">{{ store.t('Ұзақтығы (минут)', 'Длительность (минуты)') }}<input v-model.number="draft.minutes" type="number" min="1" max="180" required></label>
        </div>
        <label class="field">{{ store.t('Сипаттама', 'Описание') }}<textarea v-model.trim="draft.description" rows="2" required maxlength="300"></textarea></label>
      </section>
      <section class="card panel form-section">
        <div class="section-title"><h2><BookOpen :size="21" />{{ store.t('Оқуға арналған мәтін', 'Текст для чтения') }}</h2><button class="button secondary small" type="button" :aria-pressed="preview" @click="preview = !preview"><Eye :size="16" />{{ preview ? store.t('Алдын ала қарауды жабу', 'Закрыть предпросмотр') : store.t('Алдын ала қарау', 'Предпросмотр') }}</button></div>
        <div class="form-grid">
          <label class="field">{{ store.t('Қазақша мәтін', 'Казахский текст') }}<textarea v-model="draft.text" lang="kk" required rows="7"></textarea></label>
          <label class="field">{{ store.t('Толық орысша аударма', 'Полный перевод на русский') }}<textarea v-model="draft.translation" lang="ru" rows="7"></textarea></label>
        </div>
        <InteractiveReader v-if="preview && draft.text.trim()" :lesson="draft" preview />
        <p v-else-if="preview" class="muted">{{ store.t('Алдын ала қарау үшін қазақша мәтін енгізіңіз.', 'Введите казахский текст для предпросмотра.') }}</p>
      </section>
      <section class="card panel form-section">
        <div class="section-title"><h2>{{ store.t('Сабақ сөздігі', 'Словарь урока') }}</h2><button type="button" class="button secondary small" @click="addWord"><Plus :size="16" />{{ store.t('Сөз қосу', 'Добавить слово') }}</button></div>
        <p class="muted">{{ store.t('Сөзді мәтіндегі тұлғасында енгізіңіз. Мысалы, «қалада» сөзінің түбір тұлғасы — «қала».', 'Введите слово в той форме, в которой оно встречается в тексте. Например, словарная форма «қалада» — «қала».') }}</p>
        <fieldset v-for="(entry, index) in draft.vocabulary" :key="index" class="builder-block">
          <legend>{{ store.t('Сөздік жазбасы', 'Словарная запись') }} {{ index + 1 }}</legend>
          <div class="builder-top"><label class="field grow">{{ store.t('Мәтіндегі сөз', 'Слово в тексте') }}<input v-model.trim="entry.word" lang="kk" required></label><button class="button ghost-danger small" type="button" @click="draft.vocabulary.splice(index, 1)"><Trash2 :size="16" />{{ store.t('Сөзді алып тастау', 'Убрать слово') }}</button></div>
          <div class="form-grid"><label class="field">{{ store.t('Сөздің түбір тұлғасы', 'Словарная форма') }}<input v-model.trim="entry.lemma" lang="kk"></label><label class="field">{{ store.t('Сөздің орысша аудармасы', 'Русский перевод слова') }}<input v-model.trim="entry.translation" lang="ru" required></label><label class="field">{{ store.t('Түсіндірме', 'Пояснение') }}<textarea v-model.trim="entry.explanation" rows="2"></textarea></label><label class="field">{{ store.t('Мысал', 'Пример') }}<textarea v-model.trim="entry.example" rows="2"></textarea></label></div>
        </fieldset>
      </section>
      <section class="card panel form-section">
        <div class="section-title"><h2><Dumbbell :size="21" />{{ store.t('Жаттығулар', 'Упражнения') }}</h2><button class="button secondary small" type="button" @click="addExercise"><Plus :size="16" />{{ store.t('Жаттығу қосу', 'Добавить упражнение') }}</button></div>
        <p v-if="!draft.exercises.length" class="muted">{{ store.t('Мәтінді түсінгенін тексеру үшін жаттығу қосыңыз.', 'Добавьте упражнение для проверки понимания текста.') }}</p>
        <ExerciseBuilder v-for="(item, index) in draft.exercises" :key="item.id" v-model="draft.exercises[index]" :number="index + 1" @remove="draft.exercises.splice(index, 1)" />
      </section>
      <section class="card panel publish-row">
        <label class="field">{{ store.t('Жариялау күйі', 'Статус публикации') }}<select v-model="draft.published"><option :value="true">{{ store.t('Жарияланған', 'Опубликован') }}</option><option :value="false">{{ store.t('Нобай', 'Черновик') }}</option></select></label>
        <button class="button primary"><Save :size="18" />{{ store.t('Сабақты сақтау', 'Сохранить урок') }}</button>
        <p v-if="error" class="warning-box" role="alert">{{ error }}</p>
      </section>
    </form>
  </div>
  <div v-else class="card"><EmptyState :title="store.t('Сабақ табылмады', 'Урок не найден')"><RouterLink class="button secondary" :to="{ name: 'manage' }">{{ store.t('Сабақтарға қайту', 'Вернуться к урокам') }}</RouterLink></EmptyState></div>
</template>
