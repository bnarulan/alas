export type Role = 'student' | 'teacher'
export type Locale = 'kk' | 'ru'
export type Theme = 'teal' | 'violet' | 'blue'
export type ExerciseType = 'choice' | 'match' | 'fill' | 'order' | 'boolean' | 'review' | 'multiple-selection' | 'inline-blanks'
export type VocabularyStatus = 'learning' | 'known'

export interface User { id: string; role: Role; name: string; nameRu: string; initials: string }
export interface Classroom { id: string; name: string; grade: number; studentIds: string[] }
export interface Word { word: string; lemma: string; translation: string; explanation: string; example: string }
export interface Pair { word: string; translation: string }
export interface ExerciseTranslation {
  texts: Record<string, string>
  vocabulary?: Word[]
  contextual?: Record<string, Record<string, string>>
}
interface ExerciseBase {
  id: string; prompt: string; instruction?: string; hint?: string; explanation?: string; translation?: ExerciseTranslation
}
export type Exercise = ExerciseBase & (
  | { type: 'choice'; options: string[]; answer: number; optionIds?: string[] }
  | { type: 'match'; pairs: Pair[] }
  | { type: 'fill'; answers: string[] }
  | { type: 'order'; words: string[]; orderMode?: 'words' | 'sentences' }
  | { type: 'boolean'; answer: boolean }
  | { type: 'review'; cards: Pair[] }
  | { type: 'multiple-selection'; instruction: string; options: { id?: string; text: string; formal: boolean; explanation: string }[] }
  | { type: 'inline-blanks'; instruction: string; questions: { parts: string[]; answers: string[]; explanation: string }[] }
)
export interface Lesson {
  id: string; title: string; subject: string; grade: number; description: string
  text: string; translation: string; vocabulary: Word[]; exercises: Exercise[]
  published: boolean; theme: Theme; minutes: number
}
export interface Assignment { id: string; classId: string; lessonId: string; due: string }
export interface SavedWord { id: string; lessonId: string; userId: string; entry: Word; status: VocabularyStatus; savedAt: number }
export interface Reading { userId: string; lessonId: string; paragraphs: number[]; completed: boolean; updatedAt: number }
export interface ResultLine { prompt: string; answer: string; expected: string; correct: boolean; explanation?: string; details?: ResultLine[] }
export interface Submission {
  id: string; userId: string; lessonId: string; exerciseId: string
  prompt: string; score: number; possible: number; lines: ResultLine[]; createdAt: number
}
export interface DemoData {
  seedRevision?: number
  users: User[]; classes: Classroom[]; lessons: Lesson[]; assignments: Assignment[]
  vocabulary: SavedWord[]; readings: Reading[]; submissions: Submission[]
}
