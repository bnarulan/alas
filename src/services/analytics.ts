import type { Submission } from '../types'

export function averageScore(submissions: Submission[]) {
  const latest = new Map<string, Submission>()
  for (const attempt of submissions) {
    const key = JSON.stringify([attempt.userId, attempt.lessonId, attempt.exerciseId])
    if (!latest.has(key) || latest.get(key)!.createdAt <= attempt.createdAt) latest.set(key, attempt)
  }
  const rows = [...latest.values()]
  const possible = rows.reduce((sum, row) => sum + row.possible, 0)
  return possible ? Math.round(rows.reduce((sum, row) => sum + row.score, 0) / possible * 100) : null
}

export function attemptsFor(submissions: Submission[], studentIds: string[], lessonIds?: string[]) {
  return submissions.filter(row => studentIds.includes(row.userId) && (!lessonIds || lessonIds.includes(row.lessonId)))
}
