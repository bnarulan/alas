import type { Exercise, ExerciseType, ResultLine } from '../types'

export const exerciseTypes: [ExerciseType, string, string][] = [
  ['choice', 'Жауап таңдау', 'Выбор ответа'],
  ['match', 'Сәйкестендіру', 'Сопоставление'],
  ['fill', 'Бос орынды толтыру', 'Заполнение пропуска'],
  ['order', 'Сөйлем құрастыру', 'Порядок слов'],
  ['boolean', 'Дұрыс / бұрыс', 'Верно / неверно'],
  ['review', 'Сөздік карточкалар', 'Карточки слов'],
  ['multiple-selection', 'Бірнеше жауап таңдау', 'Выбор нескольких ответов'],
  ['inline-blanks', 'Бос орындарды толтыру', 'Заполнение пропусков'],
]

export function choiceOptionIds(exercise: Extract<Exercise, { type: 'choice' }>) {
  return exercise.options.map((_, index) => exercise.optionIds?.[index] ?? 'option-' + index)
}

export interface ExerciseAnswer {
  choice: number | null
  text: string
  order: string[]
  pairs: string[]
  cards: string[]
  truth: boolean | null
  selections: number[]
  blanks: Record<string, string>
}

export function newAnswer(): ExerciseAnswer {
  return { choice: null, text: '', order: [], pairs: [], cards: [], truth: null, selections: [], blanks: {} }
}

const normalize = (text: string) => text.normalize('NFC').toLocaleLowerCase().trim()
  .replace(/ё/gu, 'е').replace(/[.!?]+$/u, '').replace(/\s+/gu, ' ')

const normalizeBlank = (text: string) => text.normalize('NFC').toLocaleLowerCase('kk').trim()
  .replace(/\s+/gu, ' ').replace(/[‐‑]/gu, '-')

export function grade(exercise: Exercise, input: ExerciseAnswer): ResultLine[] {
  const line = (prompt: string, answer: string, expected: string, correct = normalize(answer) === normalize(expected)): ResultLine =>
    ({ prompt, answer, expected, correct })
  switch (exercise.type) {
    case 'multiple-selection': return exercise.options.map((option, i) => {
      const selected = input.selections.includes(i)
      return { ...line(option.text, selected ? 'Белгіленді' : 'Белгіленбеді', option.formal ? 'Ресми стиль' : 'Бейресми стиль', selected === option.formal), explanation: option.explanation }
    })
    case 'inline-blanks': return exercise.questions.map((question, i) => {
      const details = question.answers.map((expected, j) => {
        const answer = input.blanks[`${i}-${j}`] ?? ''
        return line(`${j + 1}-бос орын`, answer, expected, normalizeBlank(answer) === normalizeBlank(expected))
      })
      return { ...line(question.parts.join('______'), details.map(item => item.answer).join(' / '), question.answers.join(' / '), details.every(item => item.correct)), explanation: question.explanation, details }
    })
    case 'choice': return [line(exercise.prompt, exercise.options[input.choice ?? -1] ?? '', exercise.options[exercise.answer], input.choice === exercise.answer)]
    case 'fill': return [line(exercise.prompt, input.text, exercise.answers.join(' / '), exercise.answers.some(answer => normalize(answer) === normalize(input.text)))]
    case 'order': return [line(exercise.prompt, input.order.join(' '), exercise.words.join(' '))]
    case 'boolean': return [line(exercise.prompt, input.truth ? 'Дұрыс' : 'Бұрыс', exercise.answer ? 'Дұрыс' : 'Бұрыс', input.truth === exercise.answer)]
    case 'match': return exercise.pairs.map((pair, i) => line(pair.word, input.pairs[i] ?? '', pair.translation))
    case 'review': return exercise.cards.map((card, i) => line(card.word, input.cards[i] ?? '', card.translation))
  }
}

export function exerciseScore(exercise: Exercise, lines: ResultLine[]) {
  if (exercise.type !== 'multiple-selection') {
    return { score: lines.filter(item => item.correct).length, possible: lines.length }
  }
  const possible = exercise.options.filter(option => option.formal).length
  const score = lines.reduce((total, item, i) => {
    const formal = exercise.options[i].formal
    return total + (item.correct && formal ? 1 : !item.correct && !formal ? -1 : 0)
  }, 0)
  return { score: Math.max(0, score), possible }
}

export function hasAnswer(exercise: Exercise, answer: ExerciseAnswer) {
  switch (exercise.type) {
    case 'multiple-selection': return answer.selections.length > 0
    case 'inline-blanks': return Object.values(answer.blanks).some(value => !!value.trim())
    case 'choice': return answer.choice !== null
    case 'fill': return !!answer.text.trim()
    case 'order': return answer.order.length === exercise.words.length
    case 'boolean': return answer.truth !== null
    case 'match': return exercise.pairs.every((_, i) => !!answer.pairs[i])
    case 'review': return exercise.cards.every((_, i) => !!answer.cards[i]?.trim())
  }
}
