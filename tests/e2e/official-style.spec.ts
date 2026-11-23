import { expect, test } from '@playwright/test'

test('updates the existing lesson and persists both Kazakh exercise results', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Оқушы ретінде кіру/ }).click()
  await expect(page.getByRole('link', { name: 'Сабақты жалғастыру' })).toBeVisible()
  await page.evaluate(() => {
    const key = 'alas.learning.v1'
    const data = JSON.parse(localStorage.getItem(key)!)
    const lesson = data.lessons.find((item: { id: string }) => item.id === 'official-style')
    lesson.exercises = ['official-choice', 'official-match', 'official-fill', 'official-order', 'official-bool', 'official-review']
      .map(id => ({ id, type: 'choice', prompt: id, options: ['A', 'B'], answer: 0 }))
    const student = data.users.find((item: { id: string }) => item.id === 'narulan')
    student.id = 'aru'
    student.name = 'Аружан Сәрсен'
    data.lessons.push({ ...lesson, id: 'city-life' })
    data.seedRevision = 2
    data.submissions.push({
      id: 'existing-attempt', userId: 'aru', lessonId: lesson.id, exerciseId: 'official-choice',
      prompt: lesson.exercises[0].prompt, score: 1, possible: 1, lines: [], createdAt: Date.now(),
    })
    localStorage.setItem(key, JSON.stringify(data))
    localStorage.setItem('alas.demo.session.v1', 'aru')
  })

  await page.reload()
  await expect(page.getByRole('heading', { name: /^Сәлем,/ })).toBeVisible()
  expect(await page.evaluate(() => {
    const data = JSON.parse(localStorage.getItem('alas.learning.v1')!)
    return {
      lessonIds: data.lessons.map((lesson: { id: string }) => lesson.id),
      studentId: data.submissions.find((submission: { id: string }) => submission.id === 'existing-attempt').userId,
    }
  })).toEqual({ lessonIds: ['official-style'], studentId: 'narulan' })
  await page.getByRole('link', { name: 'Сабақты жалғастыру' }).click()
  await expect(page.locator('.reading-copy')).toBeVisible()
  await page.getByRole('button', { name: 'Жаттығулар 2' }).click()
  await expect(page.locator('.exercise-card')).toHaveCount(2)
  await expect(page.locator('.exercise-card .badge.teal')).toHaveText([/^1 ·/, /^2 ·/])
  await expect(page.locator('.practice-stack .section-title')).toContainText('0 / 2')

  const selection = page.locator('.exercise-card').filter({ has: page.getByRole('heading', { name: 'Ресми немесе бейресми стиль' }) })
  const choices = selection.getByRole('checkbox')
  await expect(choices).toHaveCount(6)
  await choices.nth(0).focus()
  await page.keyboard.press('Space')
  await selection.getByRole('button', { name: 'Тексеру' }).click()
  await expect(selection.locator('.feedback-summary')).toContainText('1 / 3')
  await selection.getByRole('button', { name: 'Қайта орындау' }).click()
  await choices.nth(1).check()
  await selection.getByRole('button', { name: 'Тексеру' }).click()
  await expect(selection.locator('.feedback-summary')).toContainText('0 / 3')
  await expect(selection.locator('.lesson-answer-incorrect')).toContainText([
    'Ресми стиль. Сыпайы, ресми өтініш білдіреді.',
    'Бейресми стиль. Күнделікті сөйлеу тіліндегі бұйрық мәнді сөйлем.',
    'Ресми стиль. Бұйрық пен жауапкершілікті бекітетін ресми құрылым.',
    'Ресми стиль. Қызметтік ақпаратты бейтарап түрде жеткізеді.',
  ])
  await selection.getByRole('button', { name: 'Қайта орындау' }).click()
  for (const index of [0, 2, 4]) await choices.nth(index).check()
  await selection.getByRole('button', { name: 'Тексеру' }).click()
  await expect(selection.locator('.feedback-summary')).toContainText('3 / 3')

  const blanks = page.locator('.exercise-card').filter({ has: page.getByRole('heading', { name: 'Бос орындарды толтырыңыз', exact: true }) })
  const fields = blanks.getByRole('textbox')
  const answers = [
    '  ӘКІМШІЛІК   БАСҚАРУ  ', 'әлеуметтік-құқықтық қатынастарда', 'іскерлік қарым-қатынастың',
    'іс қағаздарын жүргізуде', 'жазбаша', 'ауызекі сөйлеу мәдениетінде',
  ]
  await expect(fields).toHaveCount(6)
  for (const [i, answer] of answers.entries()) if (i !== 2) await fields.nth(i).fill(answer)
  await blanks.getByRole('button', { name: 'Тексеру' }).click()
  await expect(blanks.locator('.feedback-summary')).toContainText('4 / 5')
  await expect(blanks.getByText(/2-бос орын · Қате/)).toContainText('іскерлік қарым-қатынастың')
  await blanks.getByRole('button', { name: 'Қайта орындау' }).click()
  for (const [i, answer] of answers.entries()) await fields.nth(i).fill(answer)
  await blanks.getByRole('button', { name: 'Тексеру' }).click()
  await expect(blanks.locator('.feedback-summary')).toContainText('5 / 5')

  await page.getByRole('button', { name: 'Мәтін оқу' }).click()
  await expect(page.locator('.reading-copy')).toBeVisible()
  await page.getByRole('button', { name: 'Жаттығулар 2' }).click()
  await page.reload()
  await expect(page.locator('.exercise-card')).toHaveCount(2)
  await expect(page.locator('.practice-stack .section-title')).toContainText('2 / 2')
  await expect(selection.locator('.feedback-summary')).toContainText('3 / 3')
  await expect(blanks.locator('.feedback-summary')).toContainText('5 / 5')
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width)
})
