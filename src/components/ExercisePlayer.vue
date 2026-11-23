<script setup lang="ts">
import { computed, provide, ref, useId, watch } from 'vue'
import { Check, CircleCheck, CircleX, Languages, Layers2, Minus, Plus, RotateCcw } from 'lucide-vue-next'
import { choiceOptionIds, exerciseScore, exerciseTypes, grade, hasAnswer, newAnswer } from '../services/exercises'
import { blankMarker, exerciseLanguage, exerciseWord, russianText } from '../services/exercise-translation'
import { normalizeWord } from '../services/dictionary'
import { usePlatform } from '../stores/platform'
import type { Exercise, Lesson, Pair } from '../types'
import ExerciseText from './ExerciseText.vue'
import TTSButton from './TTSButton.vue'
import WordPopover from './WordPopover.vue'

const props = defineProps<{ lesson: Lesson; exercise: Exercise; number: number }>()
const store = usePlatform()
const input = ref(newAnswer())
const retrying = ref(false)
const translated = ref(false)
const popup = ref<InstanceType<typeof WordPopover>>()
const fieldId = useId()
const selectedOptions = ref<string[]>([])
const selectedTokens = ref<number[]>([])
const reviewIndex = ref(0)
const last = computed(() => store.latestResult(props.lesson.id, props.exercise.id))
const submitted = computed(() => retrying.value ? undefined : last.value)
const type = computed(() => exerciseTypes.find(([key]) => key === props.exercise.type)!)
const options = computed(() => {
  const exercise = props.exercise
  if (exercise.type === 'choice') {
    const ids = choiceOptionIds(exercise)
    return exercise.options.map((text, i) => ({ id: ids[i], text }))
  }
  if (exercise.type === 'multiple-selection') {
    return exercise.options.map((option, i) => ({ id: option.id ?? 'option-' + i, text: option.text }))
  }
  return []
})
function selectOption(id: string, checked: boolean) {
  if (props.exercise.type === 'choice') {
    selectedOptions.value = [id]
    input.value.choice = options.value.findIndex(option => option.id === id)
  } else {
    selectedOptions.value = checked ? [...selectedOptions.value, id] : selectedOptions.value.filter(option => option !== id)
    input.value.selections = options.value.flatMap((option, i) => selectedOptions.value.includes(option.id) ? [i] : [])
  }
}
provide(exerciseLanguage, {
  visible: () => translated.value,
  translation: (source, explicit) => translated.value ? explicit ?? russianText(props.exercise, source) : undefined,
  saved: word => !!store.savedWord(props.lesson.id, { word }),
  openWord(source, token, button, entry) {
    const pairWord = entry && normalizeWord(entry.word) === normalizeWord(token) ? entry : undefined
    void popup.value?.open(token, button, pairWord ?? exerciseWord(props.lesson, props.exercise, source, token))
  },
})
const pairEntry = (pair: Pair) => ({ ...pair, lemma: '', explanation: '', example: '' })
function reorder<T>(rows: T[]) { return rows.length > 1 ? [...rows.slice(1), rows[0]] : rows }
const tokens = computed(() => props.exercise.type === 'order' ? reorder(props.exercise.words.map((word, id) => ({ word, id }))) : [])
const matchOptions = computed(() => props.exercise.type === 'match' ? reorder([...new Set(props.exercise.pairs.map(pair => pair.translation))]) : [])
const reviewCard = computed(() => props.exercise.type === 'review' ? props.exercise.cards[reviewIndex.value] : undefined)
const orderHint = computed(() => props.exercise.type === 'order' && props.exercise.orderMode === 'sentences'
  ? ['Сөйлемдерді ретімен қосыңыз.', 'Добавляйте предложения по порядку.']
  : ['Сөздерді ретімен қосыңыз.', 'Добавляйте слова по порядку.'])
watch(selectedTokens, list => {
  input.value.order = list.map(id => tokens.value.find(item => item.id === id)!.word)
}, { deep: true, flush: 'sync' })
function submit() {
  if (!hasAnswer(props.exercise, input.value) || submitted.value) return
  popup.value?.close()
  const lines = grade(props.exercise, input.value)
  store.submit({ lessonId: props.lesson.id, exerciseId: props.exercise.id, prompt: props.exercise.prompt,
    ...exerciseScore(props.exercise, lines), lines })
  retrying.value = false
}
function retry() {
  popup.value?.close()
  input.value = newAnswer()
  selectedOptions.value = []
  selectedTokens.value = []
  reviewIndex.value = 0
  retrying.value = true
}
const checkLabel = ['Тексеру', 'Проверить']
const retryLabel = ['Қайта орындау', 'Повторить']
const backLabel = ['Алдыңғы', 'Назад']
const nextLabel = ['Келесі', 'Далее']
const feedbackLabel = computed(() => submitted.value?.score === submitted.value?.possible
  ? ['Дұрыс жауап!', 'Верно!'] : ['Жауаптар тексерілді', 'Ответы проверены'])
const booleanRu = (value: string) => value === 'Дұрыс' ? 'Верно' : 'Неверно'
const selectionRu: Record<string, string> = { Белгіленді: 'Отмечено', Белгіленбеді: 'Не отмечено' }
</script>

<template>
  <article class="card exercise-card">
    <header class="exercise-header">
      <span class="badge teal">{{ number }} · <ExerciseText :text="type[1]" :ru="type[2]" /></span>
      <div class="exercise-actions">
        <span v-if="last" class="badge slate">{{ last.score }} / {{ last.possible }}</span>
        <button type="button" class="button secondary small" :aria-pressed="translated" @click="translated = !translated">
          <Languages :size="17" /> {{ store.t('Аударма', 'Перевод') }}
        </button>
      </div>
    </header>
    <h3><ExerciseText :text="exercise.prompt" missing /></h3>
    <p v-if="exercise.instruction" class="exercise-instruction"><ExerciseText :text="exercise.instruction" missing /></p>
    <form v-if="!submitted" class="exercise-form" @submit.prevent="submit">
      <p v-if="exercise.hint" class="muted"><ExerciseText :text="exercise.hint" missing /></p>
      <div v-if="options.length" class="exercise-options">
        <p v-if="exercise.type === 'multiple-selection'" class="muted"><ExerciseText
          text="Әр дұрыс белгіге 1 ұпай беріледі, әр қате белгі 1 ұпайды шегереді."
          ru="За каждый верно отмеченный вариант начисляется 1 балл, за каждый ошибочно отмеченный вариант снимается 1 балл." /></p>
        <div v-for="option in options" :key="option.id" class="exercise-option">
          <input :id="`${fieldId}-${option.id}`" :name="fieldId" :type="exercise.type === 'choice' ? 'radio' : 'checkbox'"
            :checked="selectedOptions.includes(option.id)" @change="selectOption(option.id, ($event.target as HTMLInputElement).checked)">
          <label class="option-hit-area" :for="`${fieldId}-${option.id}`"><span class="sr-only">{{ option.text }}</span></label>
          <ExerciseText :text="option.text" missing />
        </div>
      </div>
      <ol v-else-if="exercise.type === 'inline-blanks'" class="exercise-blanks" lang="kk">
        <li v-for="(question, i) in exercise.questions" :key="i">
          <template v-for="(part, j) in question.parts" :key="j"><ExerciseText :text="part" :context="question.parts.join(blankMarker)" words-only /><input v-if="j < question.answers.length" v-model="input.blanks[`${i}-${j}`]" :aria-label="`${i + 1}-сұрақ, ${j + 1}-бос орын`" autocomplete="off" spellcheck="false"></template>
          <span v-if="translated" class="exercise-translation" lang="ru">{{ russianText(exercise, question.parts.join(blankMarker)) || 'Перевод недоступен' }}</span>
        </li>
      </ol>
      <div v-else-if="exercise.type === 'boolean'" class="exercise-options boolean-options">
        <div v-for="value in [true, false]" :key="String(value)" class="exercise-option">
          <input :id="`${fieldId}-${value}`" v-model="input.truth" type="radio" :name="fieldId" :value="value">
          <label class="option-hit-area" :for="`${fieldId}-${value}`"><span class="sr-only">{{ value ? 'Дұрыс' : 'Бұрыс' }}</span></label>
          <ExerciseText :text="value ? 'Дұрыс' : 'Бұрыс'" :ru="value ? 'Верно' : 'Неверно'" />
        </div>
      </div>
      <div v-else-if="exercise.type === 'fill'" class="field">
        <ExerciseText text="Жауабыңыз" ru="Ваш ответ" />
        <input v-model="input.text" autocomplete="off" aria-label="Жауабыңыз" placeholder="Сөзді жазыңыз">
        <small v-if="translated" class="exercise-translation" lang="ru">Напишите слово</small>
      </div>
      <div v-else-if="exercise.type === 'match'" class="exercise-match">
        <div v-for="(pair, i) in exercise.pairs" :key="i" class="match-row">
          <strong><ExerciseText :text="pair.word" :ru="pair.translation" :entry="pairEntry(pair)" /></strong>
          <select v-model="input.pairs[i]" :aria-label="`Аударманы таңдаңыз: ${pair.word}`">
            <option disabled :value="undefined">{{ translated ? 'Аударманы таңдаңыз / Выберите перевод' : 'Аударманы таңдаңыз' }}</option>
            <option v-for="option in matchOptions" :key="option" lang="ru">{{ option }}</option>
          </select>
        </div>
      </div>
      <div v-else-if="exercise.type === 'order'" class="order-exercise">
        <div class="order-selected" :aria-label="store.t('Құрастырылған жауап', 'Собранный ответ')">
          <span v-if="!selectedTokens.length" class="muted"><ExerciseText :text="orderHint[0]" :ru="orderHint[1]" /></span>
          <div v-for="(tokenId, index) in selectedTokens" :key="tokenId" class="order-chip">
            <ExerciseText :text="exercise.words[tokenId]" missing />
            <button type="button" class="order-action" :aria-label="`${store.t('Алып тастау', 'Убрать')}: ${exercise.words[tokenId]}`" @click="selectedTokens.splice(index, 1)"><Minus :size="16" /></button>
          </div>
        </div>
        <div class="order-options">
          <div v-for="token in tokens" :key="token.id" class="order-chip">
            <ExerciseText :text="token.word" missing />
            <button type="button" class="order-action" :aria-label="`${store.t('Қосу', 'Добавить')}: ${token.word}`" :disabled="selectedTokens.includes(token.id)" @click="selectedTokens.push(token.id)"><Plus :size="16" /></button>
          </div>
        </div>
      </div>
      <div v-else-if="exercise.type === 'review' && reviewCard" class="review-exercise">
        <div class="review-flashcard"><Layers2 :size="20" /><strong><ExerciseText :text="reviewCard.word" :ru="reviewCard.translation" :entry="pairEntry(reviewCard)" /></strong><TTSButton :text="reviewCard.word" language="kk" /><span>{{ reviewIndex + 1 }} / {{ exercise.cards.length }}</span></div>
        <div class="field"><ExerciseText text="Орысша аудармасы" ru="Перевод на русский" /><input v-model="input.cards[reviewIndex]" aria-label="Орысша аудармасы" autocomplete="off" lang="ru"></div>
        <div class="flash-controls">
          <button type="button" class="button secondary small" :disabled="reviewIndex === 0" @click="popup?.close(); reviewIndex--"><span>{{ backLabel[0] }}<span v-if="translated" class="exercise-translation" lang="ru">{{ backLabel[1] }}</span></span></button>
          <button type="button" class="button secondary small" :disabled="reviewIndex >= exercise.cards.length - 1" @click="popup?.close(); reviewIndex++"><span>{{ nextLabel[0] }}<span v-if="translated" class="exercise-translation" lang="ru">{{ nextLabel[1] }}</span></span></button>
        </div>
      </div>
      <button class="button primary" :disabled="!hasAnswer(exercise, input)"><Check :size="17" /><span>{{ checkLabel[0] }}<span v-if="translated" class="exercise-translation" lang="ru">{{ checkLabel[1] }}</span></span></button>
    </form>
    <div v-else class="exercise-feedback" aria-live="polite">
      <div class="feedback-summary" :class="submitted.score === submitted.possible ? 'success' : 'partial'">
        <component :is="submitted.score === submitted.possible ? CircleCheck : CircleX" :size="21" />
        <strong><ExerciseText :text="feedbackLabel[0]" :ru="feedbackLabel[1]" /> · {{ submitted.score }} / {{ submitted.possible }}</strong>
      </div>
      <div v-for="(line, index) in submitted.lines" :key="index" class="answer-line lesson-answer" :class="line.correct ? 'lesson-answer-correct' : 'lesson-answer-incorrect'">
        <span class="answer-mark" :class="{ good: line.correct }"><component :is="line.correct ? CircleCheck : CircleX" :size="17" /></span>
        <div>
          <div v-if="exercise.type === 'review' || exercise.type === 'match'" class="answer-audio-line">
            <strong><ExerciseText :text="line.prompt" :ru="line.expected" :entry="pairEntry({ word: line.prompt, translation: line.expected })" /></strong>
            <TTSButton v-if="exercise.type === 'review'" :text="line.prompt" language="kk" />
          </div>
          <strong v-else-if="submitted.lines.length > 1">{{ index + 1 }}. <ExerciseText :text="line.prompt" missing /></strong>
          <p><ExerciseText :text="line.correct ? 'Дұрыс' : 'Қате'" :ru="line.correct ? 'Верно' : 'Неверно'" /></p>
          <p v-if="exercise.type === 'multiple-selection'"><ExerciseText :text="line.answer" :ru="selectionRu[line.answer]" /></p>
          <template v-else-if="line.details">
            <div v-for="(detail, blankIndex) in line.details" :key="blankIndex" class="blank-feedback" :class="detail.correct ? 'answer-mark good' : 'answer-mark'">
              <ExerciseText :text="detail.prompt" :ru="`Пропуск ${blankIndex + 1}`" /> · <ExerciseText :text="detail.correct ? 'Дұрыс' : 'Қате'" :ru="detail.correct ? 'Верно' : 'Неверно'" /> ·
              <ExerciseText v-if="detail.answer" :text="detail.answer" />
              <ExerciseText v-else text="Жауап берілмеді" ru="Ответ не дан" />
              <template v-if="!detail.correct"> · <ExerciseText text="Дұрыс жауап" ru="Правильный ответ" />: <ExerciseText :text="detail.expected" /></template>
            </div>
          </template>
          <template v-else>
            <p><ExerciseText text="Жауабыңыз" ru="Ваш ответ" /> ·
              <span v-if="exercise.type === 'match' || exercise.type === 'review'" lang="ru">{{ line.answer }}</span>
              <ExerciseText v-else :text="line.answer" :ru="exercise.type === 'boolean' ? booleanRu(line.answer) : undefined" />
            </p>
            <div class="answer-audio-line"><p><ExerciseText text="Дұрыс жауап" ru="Правильный ответ" /> ·
              <b v-if="exercise.type === 'match' || exercise.type === 'review'" lang="ru">{{ line.expected }}</b>
              <b v-else><ExerciseText :text="line.expected" :ru="exercise.type === 'boolean' ? booleanRu(line.expected) : undefined" /></b>
            </p><TTSButton v-if="exercise.type === 'review'" :text="line.expected" language="ru" /></div>
          </template>
          <p v-if="line.explanation"><ExerciseText :text="line.explanation" missing /></p>
        </div>
      </div>
      <p v-if="exercise.explanation"><ExerciseText :text="exercise.explanation" missing /></p>
      <button type="button" class="button secondary small" @click="retry"><RotateCcw :size="16" /><span>{{ retryLabel[0] }}<span v-if="translated" class="exercise-translation" lang="ru">{{ retryLabel[1] }}</span></span></button>
    </div>
    <WordPopover ref="popup" :lesson-id="lesson.id" />
  </article>
</template>
