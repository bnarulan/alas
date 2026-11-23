
import type { InjectionKey } from 'vue'
import type { Exercise, Lesson, Word } from '../types'
import { dictionary, normalizeWord } from './dictionary'

export const blankMarker = '______'

export interface ExerciseLanguage {
  visible(): boolean
  translation(source: string, explicit?: string): string | undefined
  openWord(
    source: string,
    token: string,
    button: HTMLButtonElement,
    entry?: Word
  ): void
  saved(word: string): boolean
}

export const exerciseLanguage: InjectionKey<ExerciseLanguage> =
  Symbol('exercise language')

// -------------------------------------------
// Text normalization
// -------------------------------------------

function normalizeText(value: string): string {
  return value
    .normalize('NFC')
    .replace(/\s+/gu, ' ')
    .trim()
}

function blankCount(value: string): number {
  return value.match(/_{2,}/gu)?.length ?? 0
}

function validTranslation(source: string, translation?: string) {
  if (!translation?.trim()) return undefined

  const result = translation.trim()

  // Prevent translation from removing answer blanks.
  if (blankCount(source) !== blankCount(result)) {
    return undefined
  }

  return result
}

function lookupTranslation(
  texts: Record<string, string> | undefined,
  source: string
): string | undefined {
  if (!texts) return undefined

  if (Object.hasOwn(texts, source)) {
    return texts[source]
  }

  const normalizedSource = normalizeText(source)

  for (const [key, value] of Object.entries(texts)) {
    if (normalizeText(key) === normalizedSource) {
      return value
    }
  }

  return undefined
}

// -------------------------------------------
// Built-in educational translations
// Lesson: Ресми-іскерлік стиль
// -------------------------------------------

const commonTranslations: Record<string, string> = {
  // General exercise UI
  'Біліміңізді бекітіңіз':
    'Закрепите свои знания',

  'Бірнеше жауап таңдау':
    'Выбор нескольких ответов',

  'Бос орындарды толтыру':
    'Заполнение пропусков',

  'Бос орындарды толтырыңыз':
    'Заполните пропуски',

  'Тексеру':
    'Проверить',

  'Қайта орындау':
    'Пройти ещё раз',

  'Дұрыс жауап':
    'Правильный ответ',

  'Қате жауап':
    'Неправильный ответ',

  // Exercise 1
  'Ресми немесе бейресми стиль':
    'Официальный или неофициальный стиль',

  'Ресми немесе бейресми стильді анықтаңыз':
    'Определите официальный или неофициальный стиль',

  'Сөйлемдердің қай стильге жататынын анықтаңыз. Ресми стильдегі сөйлемдерді белгілеңіз.':
    'Определите, к какому стилю относятся предложения. Отметьте предложения в официально-деловом стиле.',

  'Әр дұрыс белгіге 1 ұпай беріледі, әр қате белгі 1 ұпайды шегереді.':
    'За каждый правильный выбор начисляется 1 балл, за каждый неправильный вычитается 1 балл.',

  'Сізден 15 қарашаға дейін есеп беруіңізді сұраймыз.':
    'Просим вас представить отчёт до 15 ноября.',

  'Ертең жиналысқа келуді ұмытпа!':
    'Не забудь завтра прийти на собрание!',

  'Осы бұйрықтың орындалуын бақылау бөлім басшысына жүктелсін.':
    'Контроль за исполнением настоящего приказа возложить на руководителя отдела.',

  'Маған құжатты тезірек жіберіп жіберші.':
    'Пришли мне документ поскорее, пожалуйста.',

  'Қызметкерлерге жаңа нұсқаулық таныстырылды.':
    'Сотрудников ознакомили с новой инструкцией.',

  'Бүгін жұмыс көп болды, қатты шаршадым.':
    'Сегодня было много работы, я очень устал(а).',

  // Exercise 2
  'Мәтін мазмұнына сүйеніп, бос орындарға тиісті сөздерді жазыңыз.':
    'Опираясь на содержание текста, впишите подходящие слова в пропуски.',

  'Ресми-іскерлік стиль ______ ісінде қолданылады.':
    'Официально-деловой стиль используется в сфере ______.',

  'Ол ______, жалпы ______ барлық түрінде қолданылады.':
    'Он используется в ______, а также во всех видах ______.',

  'Ресми-іскерлік стиль ______ қолданылады.':
    'Официально-деловой стиль используется при ______.',

  'Ол іскерлік құжаттар тілінде ______ түрде пайдаланылады.':
    'В деловых документах он используется в ______ форме.',

  'Сонымен қатар іскерлік қарым-қатынастағы ______ қолданылады.':
    'Кроме того, он используется в ______ при деловом общении.',

  // General feedback
  'Ресми стиль':
    'Официально-деловой стиль',

  'Бейресми стиль':
    'Неофициальный стиль',

  'Бұл ресми стильдегі сөйлем.':
    'Это предложение официально-делового стиля.',

  'Бұл бейресми стильдегі сөйлем.':
    'Это предложение неофициального стиля.',
}

// -------------------------------------------
// Translation of exercise content
// -------------------------------------------

export function russianText(
  exercise: Exercise,
  source: string,
  explicit?: string
): string | undefined {
  if (!source?.trim()) return undefined

  // Priority 1: explicit translation passed by component.
  const direct = validTranslation(source, explicit)
  if (direct) return direct

  // Priority 2: exercise-specific translations.
  const custom = lookupTranslation(
    exercise.translation?.texts,
    source
  )

  const checkedCustom = validTranslation(source, custom)
  if (checkedCustom) return checkedCustom

  // Priority 3: reviewed built-in translations.
  const fallback = lookupTranslation(
    commonTranslations,
    source
  )

  return validTranslation(source, fallback)
}

// -------------------------------------------
// Individual word translations
// -------------------------------------------

const exerciseUiWords: Record<string, string> = {
  қай: 'который',
  жауап: 'ответ',
  жауаптар: 'ответы',
  жауабы: 'ответ',
  жауабыңыз: 'ваш ответ',
  таңдау: 'выбор',
  таңдаңыз: 'выберите',
  белгілеңіз: 'отметьте',
  сәйкестендіру: 'сопоставление',
  бос: 'пустой',
  орын: 'место, пропуск',
  орынды: 'место, пропуск',
  орындарды: 'места, пропуски',
  толтыру: 'заполнение',
  толтырыңыз: 'заполните',
  сөйлем: 'предложение',
  сөйлемдерді: 'предложения',
  сөйлемдердің: 'предложений',
  сөздерді: 'слова',
  сөздік: 'словарь',
  карточкалар: 'карточки',
  бірнеше: 'несколько',
  әр: 'каждый',
  дұрыс: 'правильно, правильный',
  бұрыс: 'неверно, неправильный',
  қате: 'ошибка, неверно',
  ұпай: 'балл',
  беріледі: 'начисляется, даётся',
  белгі: 'отметка',
  белгіге: 'за отметку',
  ұпайды: 'балл',
  шегереді: 'вычитает',
  ретімен: 'по порядку',
  қосыңыз: 'добавьте',
  орысша: 'по-русски',
  аударма: 'перевод',
  аудармасы: 'перевод',
  тексерілді: 'проверено',
  белгіленді: 'отмечено',
  белгіленбеді: 'не отмечено',
  берілмеді: 'не дано',

  // Lesson-specific words
  ресми: 'официальный',
  бейресми: 'неофициальный',
  стиль: 'стиль',
  стильдегі: 'в данном стиле',
  іскерлік: 'деловой',
  әкімшілік: 'административный',
  басқару: 'управление',
  қатынастарда: 'в отношениях',
  құжат: 'документ',
  құжатты: 'документ',
  құжаттар: 'документы',
  бұйрық: 'приказ',
  бұйрықтың: 'приказа',
  нұсқаулық: 'инструкция',
  нұсқаулықтар: 'инструкции',
  қызметкерлерге: 'сотрудникам',
  жиналысқа: 'на собрание',
  есеп: 'отчёт',
  есепті: 'отчёт',
  жазбаша: 'письменно, письменный',
  ауызекі: 'разговорный, устный',
  сөйлеу: 'речь, говорить',
  заң: 'закон',
  қаулы: 'постановление',
  баяндамалар: 'доклады',
  қолданылады: 'используется',
  пайдаланылады: 'применяется',
}

function contextualGloss(
  exercise: Exercise,
  source: string,
  token: string
): string | undefined {
  const contextual = exercise.translation?.contextual

  if (!contextual) return undefined

  const context =
    contextual[source] ??
    Object.entries(contextual).find(
      ([key]) => normalizeText(key) === normalizeText(source)
    )?.[1]

  if (!context) return undefined

  const normalizedToken = normalizeWord(token)

  for (const [word, translation] of Object.entries(context)) {
    if (normalizeWord(word) === normalizedToken) {
      return translation?.trim() || undefined
    }
  }

  return undefined
}

export function exerciseWord(
  lesson: Lesson,
  exercise: Exercise,
  source: string,
  token: string
): Word | undefined {
  const key = normalizeWord(token)

  if (!key) return undefined

  // Exercise-specific vocabulary first.
  const vocabularyEntry =
    exercise.translation?.vocabulary?.find(
      word =>
        normalizeWord(word.word) === key &&
        word.translation.trim()
    )

  // Lesson-wide dictionary.
  const entry =
    vocabularyEntry ??
    dictionary.lookup(lesson, token)

  // Exact contextual translation has priority.
  const contextTranslation = contextualGloss(
    exercise,
    source,
    token
  )

  if (contextTranslation) {
    return {
      word: token,
      lemma: entry?.lemma ?? '',
      explanation: entry?.explanation ?? '',
      example: source,
      translation: contextTranslation,
    }
  }

  if (entry?.translation?.trim()) {
    return entry
  }

  // Built-in translation for exercise terminology.
  const fallback = exerciseUiWords[key]

  if (!fallback) return undefined

  return {
    word: token,
    lemma: '',
    explanation: '',
    example: source,
    translation: fallback,
  }
}

// -------------------------------------------
// Collect translatable exercise content
// -------------------------------------------

export function exerciseSources(
  exercise: Exercise
): string[] {
  const sources: string[] = [
    exercise.prompt,
    exercise.instruction ?? '',
    exercise.hint ?? '',
    exercise.explanation ?? '',
  ]

  switch (exercise.type) {
    case 'choice':
      sources.push(...exercise.options)
      break

    case 'fill':
      // Do not expose correct answers before submission.
      // The prompt is already included above.
      break

    case 'order':
      // Only collect displayed words.
      // Do not automatically expose the solved order.
      sources.push(...exercise.words)
      break

    case 'multiple-selection':
      sources.push(
        ...exercise.options.flatMap(option => [
          option.text,
          option.explanation,
        ])
      )
      break

    case 'inline-blanks':
      sources.push(
        ...exercise.questions.flatMap(question => [
          question.parts.join(blankMarker),
          question.explanation,
        ])
      )
      break
  }

  return [
    ...new Set(
      sources
        .filter(Boolean)
        .map(source => normalizeText(source))
    ),
  ]
}
