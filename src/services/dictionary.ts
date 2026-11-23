import type { Lesson, Word } from '../types'

export function normalizeWord(value: string) {
  return value.normalize('NFC').toLocaleLowerCase('kk').trim().replace(/[‐‑–]/gu, '-')
}

export function splitParagraphs(text: string) {
  return text.split(/(\r?\n[\t ]*\r?\n(?:[\t ]*\r?\n)*)/u)
}

export function tokenize(text: string) {
  return (text.match(/[\p{L}\p{M}]+(?:[-‐‑’'][\p{L}\p{M}]+)*|[^\p{L}\p{M}]+/gu) ?? [])
    .map(value => ({ value, isWord: /^\p{L}/u.test(value) }))
}

export interface DictionaryService {
  lookup(lesson: Lesson, token: string): Word | undefined
  translation(lesson: Lesson): string
}

export const dictionary: DictionaryService = {
  lookup: (lesson, token) => lesson.vocabulary.find(entry => normalizeWord(entry.word) === normalizeWord(token)),
  translation: lesson => lesson.translation,
}
