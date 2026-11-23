import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { makeSeed } from '../data/seed'
import { newId } from '../services/identifiers'
import { demoAuth } from '../services/demo-auth'
import { normalizeWord, splitParagraphs } from '../services/dictionary'
import { learningRepository } from '../services/repository'
import type { Assignment, Classroom, Lesson, Locale, Role, Submission, VocabularyStatus, Word } from '../types'

const localeKey = 'alas.locale.v1'
function readLocale(): Locale {
  try { return localStorage.getItem(localeKey) === 'ru' ? 'ru' : 'kk' } catch { return 'kk' }
}

export const usePlatform = defineStore('platform', () => {
  const data = ref(makeSeed())
  const userId = ref(demoAuth.current())
  const locale = ref<Locale>(readLocale())
  const storageError = ref(false)
  const user = computed(() => data.value.users.find(item => item.id === userId.value))
  const catalog = computed(() => data.value.lessons.filter(lesson => lesson.published))
  const myWords = computed(() => data.value.vocabulary.filter(word => word.userId === userId.value).sort((a, b) => b.savedAt - a.savedAt))
  const myAssignments = computed(() => data.value.assignments.filter(assignment =>
    data.value.classes.some(group => group.id === assignment.classId && group.studentIds.includes(userId.value ?? ''))
      && catalog.value.some(lesson => lesson.id === assignment.lessonId)))
  const t = (kk: string, ru: string) => locale.value === 'kk' ? kk : ru

  async function initialize() { data.value = await learningRepository.load() }
  function persist() { void learningRepository.save(data.value).then(() => { storageError.value = false }, () => { storageError.value = true }) }
  function setLocale(value: Locale) {
    locale.value = value
    document.documentElement.lang = value
    try { localStorage.setItem(localeKey, value) } catch { /* Keep this session's preference. */ }
  }
  function signIn(role: Role) { userId.value = demoAuth.signIn(role) }
  function signOut() { demoAuth.signOut(); userId.value = null }
  async function reset() {
    try { data.value = await learningRepository.reset(); storageError.value = false }
    catch { data.value = makeSeed(); storageError.value = true }
  }
  function reading(lessonId: string, studentId = userId.value) {
    return data.value.readings.find(item => item.userId === studentId && item.lessonId === lessonId)
  }
  function recordReading(lessonId: string, paragraph?: number) {
    if (!studentCanAccess(lessonId) || !userId.value) return
    const lesson = catalog.value.find(item => item.id === lessonId)!
    const total = Math.ceil(splitParagraphs(lesson.text).length / 2)
    const existing = reading(lessonId)
    if (paragraph !== undefined && existing?.paragraphs.includes(paragraph)) return
    const paragraphs = paragraph === undefined ? Array.from({ length: total }, (_, i) => i) : [...(existing?.paragraphs ?? []), paragraph]
    const updated = { lessonId, userId: userId.value, paragraphs, completed: paragraphs.length >= total, updatedAt: Date.now() }
    if (existing) Object.assign(existing, updated)
    else data.value.readings.push(updated)
    persist()
  }
  function readingPercent(lesson: Lesson, studentId = userId.value) {
    const total = Math.ceil(splitParagraphs(lesson.text).length / 2)
    const stored = reading(lesson.id, studentId)
    return stored?.completed ? 100 : Math.min(99, Math.round((stored?.paragraphs.length ?? 0) / total * 100))
  }
  function latestResult(lessonId: string, exerciseId: string, studentId = userId.value) {
    const submissions = data.value.submissions
    for (let i = submissions.length - 1; i >= 0; i--) {
      const item = submissions[i]
      if (item.userId === studentId && item.lessonId === lessonId && item.exerciseId === exerciseId) return item
    }
  }
  function lessonProgress(lesson: Lesson, studentId = userId.value) {
    const results = lesson.exercises.filter(exercise => latestResult(lesson.id, exercise.id, studentId)).length
    const read = readingPercent(lesson, studentId)
    if (read === 100 && results === lesson.exercises.length) return 100
    return Math.min(99, Math.round((read + results * 100) / (lesson.exercises.length + 1)))
  }
  const completed = computed(() => catalog.value.filter(lesson => lessonProgress(lesson) === 100).length)
  const points = computed(() => {
    const best = new Map<string, number>()
    data.value.submissions.filter(item => item.userId === userId.value).forEach(item => {
      const key = item.lessonId + ':' + item.exerciseId
      best.set(key, Math.max(item.score, best.get(key) ?? 0))
    })
    return [...best.values()].reduce((sum, score) => sum + score * 10, 0) + completed.value * 20
  })
  function studentCanAccess(lessonId: string) { return user.value?.role === 'student' && catalog.value.some(lesson => lesson.id === lessonId) }
  function savedWord(lessonId: string, entry: Pick<Word, 'word'>) {
    return myWords.value.find(item => item.lessonId === lessonId && normalizeWord(item.entry.word) === normalizeWord(entry.word))
  }
  function toggleWord(lessonId: string, entry: Word) {
    if (!studentCanAccess(lessonId) || !userId.value) return
    const saved = savedWord(lessonId, entry)
    if (saved) data.value.vocabulary = data.value.vocabulary.filter(item => item.id !== saved.id)
    else data.value.vocabulary.push({ id: newId(), userId: userId.value, lessonId, entry: { ...entry }, status: 'learning', savedAt: Date.now() })
    persist()
  }
  function updateWord(id: string, status: VocabularyStatus) {
    const saved = myWords.value.find(item => item.id === id)
    if (!saved || user.value?.role !== 'student') return
    saved.status = status
    persist()
  }
  function removeWord(id: string) {
    if (user.value?.role !== 'student') return
    data.value.vocabulary = data.value.vocabulary.filter(item => item.id !== id || item.userId !== userId.value)
    persist()
  }
  function submit(result: Omit<Submission, 'id' | 'userId' | 'createdAt'>) {
    if (!studentCanAccess(result.lessonId) || !userId.value) return
    const submission = { ...result, id: newId(), userId: userId.value, createdAt: Date.now() }
    data.value.submissions.push(submission)
    persist()
    return submission
  }
  function saveLesson(lesson: Lesson) {
    if (user.value?.role !== 'teacher') return
    const index = data.value.lessons.findIndex(item => item.id === lesson.id)
    if (index >= 0) {
      if (data.value.lessons[index].text !== lesson.text)
        data.value.readings = data.value.readings.filter(item => item.lessonId !== lesson.id)
      data.value.lessons[index] = lesson
    } else data.value.lessons.push(lesson)
    persist()
  }
  function deleteLesson(id: string) {
    if (user.value?.role !== 'teacher') return
    data.value.lessons = data.value.lessons.filter(item => item.id !== id)
    data.value.assignments = data.value.assignments.filter(item => item.lessonId !== id)
    data.value.readings = data.value.readings.filter(item => item.lessonId !== id)
    data.value.submissions = data.value.submissions.filter(item => item.lessonId !== id)
    persist()
  }
  function saveClass(group: Classroom) {
    if (user.value?.role !== 'teacher') return
    const index = data.value.classes.findIndex(item => item.id === group.id)
    if (index < 0) data.value.classes.push(group)
    else data.value.classes[index] = group
    persist()
  }
  function deleteClass(id: string) {
    if (user.value?.role !== 'teacher') return
    data.value.classes = data.value.classes.filter(item => item.id !== id)
    data.value.assignments = data.value.assignments.filter(item => item.classId !== id)
    persist()
  }
  function assign(assignment: Assignment) {
    if (user.value?.role !== 'teacher' || !catalog.value.some(item => item.id === assignment.lessonId)
      || !data.value.classes.some(group => group.id === assignment.classId)) return
    const existing = data.value.assignments.find(item => item.classId === assignment.classId && item.lessonId === assignment.lessonId)
    if (existing) existing.due = assignment.due
    else data.value.assignments.push(assignment)
    persist()
  }
  function removeAssignment(id: string) {
    if (user.value?.role !== 'teacher') return
    data.value.assignments = data.value.assignments.filter(item => item.id !== id)
    persist()
  }

  return { data, user, locale, catalog, myWords, myAssignments, points, completed, storageError, t, initialize, setLocale,
    signIn, signOut, reset, reading, recordReading, readingPercent, latestResult, lessonProgress, toggleWord, savedWord,
    updateWord, removeWord, submit, saveLesson, deleteLesson, saveClass, deleteClass, assign, removeAssignment }
})
