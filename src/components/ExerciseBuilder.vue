<script setup lang="ts">
import { computed, ref } from 'vue'
import { Plus, Trash2 } from 'lucide-vue-next'
import { choiceOptionIds, exerciseTypes } from '../services/exercises'
import { exerciseSources } from '../services/exercise-translation'
import { newId } from '../services/identifiers'
import { usePlatform } from '../stores/platform'
import type { Exercise, ExerciseType } from '../types'

const exercise = defineModel<Exercise>({ required: true })
const props = defineProps<{ number: number }>()
const emit = defineEmits<{ remove: [] }>()
const store = usePlatform()
const sentence = ref(exercise.value.type === 'order' ? exercise.value.words.join(exercise.value.orderMode === 'sentences' ? '\n' : ' ') : '')
const currentPairs = computed(() => exercise.value.type === 'match' ? exercise.value.pairs : exercise.value.type === 'review' ? exercise.value.cards : [])
const builtIn = computed(() => exercise.value.type === 'multiple-selection' || exercise.value.type === 'inline-blanks')
const editableTypes = exerciseTypes.filter(([type]) => type !== 'multiple-selection' && type !== 'inline-blanks')
const sources = computed(() => exerciseSources(exercise.value))
function setTranslation(source: string, event: Event) {
  const text = (event.target as HTMLInputElement).value.trim()
  const translation = (exercise.value.translation ??= { texts: {} })
  if (text) translation.texts = { ...translation.texts, [source]: text }
  else delete translation.texts[source]
}
function addGloss() {
  const translation = (exercise.value.translation ??= { texts: {} })
  const vocabulary = (translation.vocabulary ??= [])
  vocabulary.push({ word: '', lemma: '', translation: '', explanation: '', example: '' })
}
function setType(value: ExerciseType) {
  const { id, prompt, translation, instruction, hint, explanation } = exercise.value
  const base = { id, prompt, translation, instruction, hint, explanation }
  switch (value) {
    case 'choice': exercise.value = { ...base, type: value, options: ['', ''], optionIds: [newId(), newId()], answer: 0 }; break
    case 'match': exercise.value = { ...base, type: value, pairs: [{ word: '', translation: '' }, { word: '', translation: '' }] }; break
    case 'fill': exercise.value = { ...base, type: value, answers: [''] }; break
    case 'order': sentence.value = ''; exercise.value = { ...base, type: value, words: [] }; break
    case 'boolean': exercise.value = { ...base, type: value, answer: true }; break
    case 'review': exercise.value = { ...base, type: value, cards: [{ word: '', translation: '' }] }; break
  }
}
function removeOption(index: number) {
  const item = exercise.value
  if (item.type !== 'choice') return
  item.optionIds ??= choiceOptionIds(item)
  item.options.splice(index, 1)
  item.optionIds.splice(index, 1)
  if (item.answer === index) item.answer = 0
  else if (item.answer > index) item.answer--
}
function addOption() {
  const item = exercise.value
  if (item.type !== 'choice') return
  item.optionIds ??= choiceOptionIds(item)
  item.optionIds.push(newId())
  item.options.push('')
}
function setWords(event: Event) {
  sentence.value = (event.target as HTMLTextAreaElement).value
  const item = exercise.value
  if (item.type === 'order') item.words = sentence.value.split(item.orderMode === 'sentences' ? /\r?\n/u : /\s+/u).map(word => word.trim()).filter(Boolean)
}
function setOrderMode(event: Event) {
  const item = exercise.value
  if (item.type !== 'order') return
  item.orderMode = (event.target as HTMLSelectElement).value === 'sentences' ? 'sentences' : 'words'
  sentence.value = item.words.join(item.orderMode === 'sentences' ? '\n' : ' ')
}
</script>

<template>
  <fieldset class="builder-block">
    <legend>{{ store.t('Жаттығу', 'Упражнение') }} {{ props.number }}</legend>
    <div class="builder-top">
      <label v-if="!builtIn" class="field grow">{{ store.t('Жаттығу түрі', 'Тип упражнения') }}<select :value="exercise.type" @change="setType(($event.target as HTMLSelectElement).value as ExerciseType)"><option v-for="[key, kk, ru] in editableTypes" :key="key" :value="key">{{ store.t(kk, ru) }}</option></select></label>
      <button type="button" class="button ghost-danger small" @click="emit('remove')"><Trash2 :size="16" />{{ store.t('Жаттығуды алып тастау', 'Убрать упражнение') }}</button>
    </div>
    <label class="field">{{ store.t('Сұрақ немесе нұсқау', 'Вопрос или инструкция') }}<input v-model.trim="exercise.prompt" required></label>
    <p v-if="builtIn" class="muted">{{ exercise.instruction }}</p>
    <template v-else-if="exercise.type === 'choice'">
      <p class="muted">{{ store.t('Жауап нұсқаларын енгізіп, дұрысын белгілеңіз.', 'Введите варианты ответа и отметьте правильный.') }}</p>
      <div v-for="(_, index) in exercise.options" :key="index" class="choice-builder">
        <input v-model="exercise.answer" type="radio" :name="exercise.id" :value="index" :aria-label="store.t('Дұрыс нұсқа', 'Правильный вариант') + ' ' + (index + 1)">
        <label class="field"><span class="sr-only">{{ store.t('Жауап нұсқасы', 'Вариант ответа') }} {{ index + 1 }}</span><input v-model.trim="exercise.options[index]" required :placeholder="store.t('Жауап нұсқасы', 'Вариант ответа') + ' ' + (index + 1)"></label>
        <button type="button" class="icon-button" :disabled="exercise.options.length <= 2" :aria-label="store.t('Нұсқаны жою', 'Удалить вариант') + ' ' + (index + 1)" @click="removeOption(index)"><Trash2 :size="16" /></button>
      </div>
      <button type="button" class="button secondary small" @click="addOption"><Plus :size="16" />{{ store.t('Нұсқа қосу', 'Добавить вариант') }}</button>
    </template>
    <template v-else-if="exercise.type === 'fill'">
      <div v-for="(_, index) in exercise.answers" :key="index" class="inline-form">
        <label class="field grow">{{ index === 0 ? store.t('Дұрыс жауап', 'Правильный ответ') : store.t('Баламалы жауап', 'Допустимый вариант') }}<input v-model.trim="exercise.answers[index]" required></label>
        <button v-if="index > 0" type="button" class="icon-button" :aria-label="store.t('Нұсқаны жою', 'Удалить вариант')" @click="exercise.answers.splice(index, 1)"><Trash2 :size="16" /></button>
      </div>
      <button type="button" class="button secondary small" @click="exercise.answers.push('')"><Plus :size="16" />{{ store.t('Баламалы жауап қосу', 'Добавить допустимый вариант') }}</button>
    </template>
    <template v-else-if="exercise.type === 'order'">
      <label class="field">{{ store.t('Реттеу түрі', 'Что нужно упорядочить') }}
        <select :value="exercise.orderMode ?? 'words'" @change="setOrderMode"><option value="words">{{ store.t('Сөздер', 'Слова') }}</option><option value="sentences">{{ store.t('Сөйлемдер', 'Предложения') }}</option></select>
      </label>
      <label class="field">{{ store.t('Дұрыс рет', 'Правильный порядок') }}<textarea required :value="sentence" @input="setWords"></textarea>
        <small>{{ exercise.orderMode === 'sentences' ? store.t('Әр сөйлемді жеке жолға жазыңыз.', 'Введите каждое предложение на отдельной строке.') : store.t('Сөздерді дұрыс ретпен жазыңыз.', 'Введите слова в правильном порядке.') }}</small>
      </label>
    </template>
    <label v-else-if="exercise.type === 'boolean'" class="field">{{ store.t('Дұрыс жауап', 'Правильный ответ') }}<select v-model="exercise.answer"><option :value="true">{{ store.t('Дұрыс', 'Верно') }}</option><option :value="false">{{ store.t('Бұрыс', 'Неверно') }}</option></select></label>
    <template v-else>
      <div v-for="(pair, index) in currentPairs" :key="index" class="pair-form">
        <label class="field">{{ store.t('Қазақша сөз', 'Слово на казахском') }}<input v-model.trim="pair.word" required></label>
        <label class="field">{{ store.t('Орысша аударма', 'Перевод на русский') }}<input v-model.trim="pair.translation" required></label>
        <button type="button" class="icon-button" :disabled="currentPairs.length <= (exercise.type === 'match' ? 2 : 1)" :aria-label="store.t('Жұпты жою', 'Удалить пару')" @click="currentPairs.splice(index, 1)"><Trash2 :size="16" /></button>
      </div>
      <button type="button" class="button secondary small" @click="currentPairs.push({ word: '', translation: '' })"><Plus :size="16" />{{ store.t('Жұп қосу', 'Добавить пару') }}</button>
    </template>
    <details class="exercise-translation-editor">
      <summary>{{ store.t('Орысша аудармалар мен сөздік', 'Переводы на русский и словарь') }}</summary>
      <label v-if="!builtIn" class="field">{{ store.t('Қосымша нұсқау', 'Дополнительная инструкция') }}<input v-model.trim="exercise.instruction" lang="kk"></label>
      <label class="field">{{ store.t('Көмек', 'Подсказка') }}<input v-model.trim="exercise.hint" lang="kk"></label>
      <label class="field">{{ store.t('Жауаптан кейінгі түсіндірме', 'Пояснение после ответа') }}<input v-model.trim="exercise.explanation" lang="kk"></label>
      <p class="muted">{{ store.t('Аудармада бос орындардың санын сақтаңыз (______ белгісі).', 'Сохраните число пропусков (обозначаются как ______) в переводе.') }}</p>
      <label v-for="source in sources" :key="source" class="field"><span lang="kk">{{ source }}</span>
        <input lang="ru" :value="exercise.translation?.texts[source] ?? ''" :placeholder="store.t('Орысша аударма', 'Перевод на русский')" @change="setTranslation(source, $event)">
      </label>
      <div v-for="(word, index) in exercise.translation?.vocabulary" :key="index" class="pair-form">
        <label class="field">{{ store.t('Қазақша сөз', 'Слово на казахском') }}<input v-model.trim="word.word" required lang="kk"></label>
        <label class="field">{{ store.t('Орысша аударма', 'Перевод на русский') }}<input v-model.trim="word.translation" required lang="ru"></label>
        <button type="button" class="icon-button" :aria-label="store.t('Сөзді жою', 'Убрать слово')" @click="exercise.translation?.vocabulary?.splice(index, 1)"><Trash2 :size="16" /></button>
      </div>
      <button type="button" class="button secondary small" @click="addGloss"><Plus :size="16" />{{ store.t('Сөз қосу', 'Добавить слово') }}</button>
    </details>
  </fieldset>
</template>
