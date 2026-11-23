import type { Lesson, Locale } from './types'

export function dateLabel(value: string | number, locale: Locale) {
  const date = typeof value === 'string' ? new Date(value + 'T12:00:00+05:00') : new Date(value)
  return new Intl.DateTimeFormat(locale === 'kk' ? 'kk-KZ' : 'ru-RU', {
    day: 'numeric', month: locale === 'kk' ? 'long' : 'short', timeZone: 'Asia/Qyzylorda',
  }).format(date)
}

export function dateInputAfter(days: number, from = Date.now()) {
  return new Intl.DateTimeFormat('sv-SE', {
    year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'Asia/Qyzylorda',
  }).format(from + days * 86400000)
}

export function subjectLabel(lesson: Lesson, locale: Locale) {
  return lesson.subject === 'Қазақ тілі' && locale === 'ru' ? 'Казахский язык' : lesson.subject
}
