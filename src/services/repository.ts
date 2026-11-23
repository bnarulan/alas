import { currentDemoUserId, demoAccounts, makeSeed, officialStyleExercises, retiredDemoLessonIds, seedRevision } from '../data/seed'
import type { DemoData } from '../types'

export interface LearningRepository {
  load(): Promise<DemoData>
  save(data: DemoData): Promise<void>
  reset(): Promise<DemoData>
}

const key = 'alas.learning.v1'
const collections = ['users', 'classes', 'lessons', 'assignments', 'vocabulary', 'readings', 'submissions'] as const
const retiredOfficialExerciseIds = new Set([
  'official-choice', 'official-match', 'official-fill', 'official-order', 'official-bool', 'official-review',
])

function isData(value: unknown): value is DemoData {
  if (!value || typeof value !== 'object') return false
  const data = value as DemoData
  return collections.every(name => Array.isArray(data[name]) && data[name].every(item => item && typeof item === 'object'))
    && data.lessons.every(lesson => lesson && typeof lesson.text === 'string'
      && Array.isArray(lesson.vocabulary) && Array.isArray(lesson.exercises))
}

export const learningRepository: LearningRepository = {
  async load() {
    try {
      const raw = localStorage.getItem(key)
      if (raw) {
        const data: unknown = JSON.parse(raw)
        if (isData(data)) {
          const revision = data.seedRevision ?? 1
          if (revision < 4) {
            for (const profile of Object.values(demoAccounts)) {
              data.users = data.users.filter(user => currentDemoUserId(user.id) !== profile.id)
              data.users.push({ ...profile })
            }
            for (const group of data.classes) {
              group.studentIds = [...new Set(group.studentIds.map(currentDemoUserId))]
            }
            for (const record of [...data.readings, ...data.vocabulary, ...data.submissions]) {
              record.userId = currentDemoUserId(record.userId)
            }
            data.lessons = data.lessons.filter(lesson => !retiredDemoLessonIds.includes(lesson.id))
            data.assignments = data.assignments.filter(item => !retiredDemoLessonIds.includes(item.lessonId))
            const exercises = data.lessons.find(lesson => lesson.id === 'official-style')?.exercises
            for (const exercise of officialStyleExercises) {
              if (exercises && !exercises.some(item => item.id === exercise.id || (item.prompt === exercise.prompt && item.type === exercise.type))) {
                exercises.push(structuredClone(exercise))
              }
            }
          }
          if (revision < 5) {
            const lesson = data.lessons.find(item => item.id === 'official-style')
            if (lesson) lesson.exercises = lesson.exercises.filter(item => !retiredOfficialExerciseIds.has(item.id))
          }
          if (revision < 6) {
            const lesson = data.lessons.find(item => item.id === 'official-style')
            for (const exercise of lesson?.exercises ?? []) {
              const seed = officialStyleExercises.find(item => item.id === exercise.id && item.type === exercise.type)?.translation
              if (!seed) continue
              exercise.translation = {
                ...exercise.translation,
                texts: { ...seed.texts, ...exercise.translation?.texts },
                contextual: { ...seed.contextual, ...exercise.translation?.contextual },
              }
            }
          }
          if (revision < seedRevision) {
            data.seedRevision = seedRevision
            await this.save(data).catch(() => undefined)
          }
          return data
        }
      }
    } catch {
      // The demo can still run when storage is unavailable or corrupt.
    }
    const seed = makeSeed()
    await this.save(seed).catch(() => undefined)
    return seed
  },
  async save(data) { localStorage.setItem(key, JSON.stringify(data)) },
  async reset() {
    const seed = makeSeed()
    await this.save(seed)
    return seed
  },
}
