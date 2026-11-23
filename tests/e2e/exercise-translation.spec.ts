import { expect, test } from '@playwright/test'
import type { Locator, Page } from '@playwright/test'
import type { Exercise } from '../../src/types'

const translate = (card: Locator) => card.getByRole('button', { name: 'Аударма', exact: true })
const check = (card: Locator) => card.getByRole('button', { name: /^Тексеру/ })

async function openPractice(page: Page) {
  await page.getByRole('link', { name: 'Сабақты жалғастыру' }).click()
  await page.getByRole('button', { name: /^Жаттығулар \d+$/ }).click()
  const cards = page.locator('.exercise-card')
  await expect(cards.first()).toBeVisible()
  return cards
}

async function openExercises(page: Page, exercises?: Exercise[]) {
  await page.goto('/')
  await page.getByRole('button', { name: /Оқушы ретінде кіру/ }).click()
  await expect(page.getByRole('heading', { name: /^Сәлем,/ })).toBeVisible()
  if (exercises) {
    await page.evaluate(items => {
      const key = 'alas.learning.v1'
      const data = JSON.parse(localStorage.getItem(key)!)
      const lesson = data.lessons[0]
      lesson.exercises = items
      localStorage.setItem(key, JSON.stringify(data))
    }, exercises)
    await page.reload()
  }
  return openPractice(page)
}

test('translates the formal-style exercise and opens an option word separately from selecting it', async ({ page, isMobile }) => {
  const card = (await openExercises(page)).first()
  const options = card.getByRole('checkbox')
  const russian = 'Не забудь завтра прийти на собрание!'
  await expect(card.getByText(russian)).toHaveCount(0)
  await options.first().check()
  await translate(card).click()
  await expect(card.getByText('Официально-деловой или неофициальный стиль', { exact: true })).toBeVisible()
  await expect(card.locator('.exercise-option .exercise-translation')).toHaveCount(6)
  await expect(card.getByText(russian)).toBeVisible()
  const token = card.getByRole('button', { name: 'жиналысқа', exact: true })
  if (isMobile) await token.tap()
  else await token.press('Enter')
  const popup = page.getByRole('dialog', { name: 'жиналысқа' })
  await expect(popup.getByText('на собрание', { exact: true })).toBeVisible()
  await expect(options.first()).toBeChecked()
  await expect(options.nth(1)).not.toBeChecked()
  const response = page.waitForResponse(item => item.url().endsWith('/api/tts'))
  await popup.getByRole('button', { name: 'Қазақша тыңдау', exact: true }).click()
  const audio = await response
  expect(audio.status()).toBe(200)
  expect(audio.headers()['content-type']).toBe('audio/mpeg')
  expect(audio.request().postDataJSON()).toMatchObject({ text: 'жиналысқа', language: 'kk' })
  await expect(popup.locator('.tts-button').first()).toHaveAttribute('data-state', 'playing')
  await popup.getByRole('button', { name: 'Сөздікке қосу' }).click()
  await popup.getByRole('button', { name: 'Жабу' }).click()
  await expect(token).toHaveClass(/word-saved/)
  await translate(card).click()
  await expect(card.getByText(russian)).toHaveCount(0)
  await expect(options.first()).toBeChecked()
  await options.nth(2).check()
  await options.nth(4).check()
  await check(card).click()
  await expect(card.locator('.feedback-summary')).toContainText('3 / 3')
  await translate(card).click()
  await expect(card.getByText('Официально-деловой стиль. Выражает вежливую официальную просьбу.')).toBeVisible()
  const { clientWidth, scrollWidth } = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }))
  expect(scrollWidth).toBeLessThanOrEqual(clientWidth)
  await page.reload()
  await expect(card.getByRole('button', { name: 'жиналысқа', exact: true })).toHaveClass(/word-saved/)
  await expect(card.locator('.feedback-summary')).toContainText('3 / 3')
})

test('preserves blank positions and answers when switching translations', async ({ page }) => {
  const card = (await openExercises(page)).nth(1)
  const fields = card.getByRole('textbox')
  await fields.first().fill('әкімшілік басқару')
  await translate(card).click()
  await expect(card.locator('.exercise-blanks .exercise-translation')).toHaveText([
    'Официально-деловой стиль применяется в сфере ______.',
    'Он используется в ______, а также во всех видах ______.',
    'Официально-деловой стиль применяется в ______.',
    'В языке деловых документов он используется в ______ форме.',
    'Кроме того, в деловом общении он используется в ______.',
  ])
  await expect(fields).toHaveCount(6)
  await expect(fields.first()).toHaveValue('әкімшілік басқару')
  await expect(card.getByText('административное управление', { exact: true })).toHaveCount(0)
  await translate(card).click()
  await expect(fields.first()).toHaveValue('әкімшілік басқару')
  await check(card).click()
  await expect(card.locator('.feedback-summary')).toContainText('1 / 5')
  await translate(card).click()
  await expect(card.getByText('Административное управление связано с организацией работы учреждения.')).toBeVisible()
})

test('renders bilingual content and grades answers across the other exercise types', async ({ page }) => {
  const exercises: Exercise[] = [
    { id: 'c', type: 'choice', prompt: 'Сөзді таңдаңыз.', hint: 'Мәтінді оқыңыз.', options: ['Өнер', 'Білім'], optionIds: ['art', 'knowledge'], answer: 1,
      translation: { texts: { 'Сөзді таңдаңыз.': 'Выберите слово.', 'Мәтінді оқыңыз.': 'Прочитайте текст.', Өнер: 'Искусство', Білім: 'Образование' } } },
    { id: 'f', type: 'fill', prompt: '___ — болашақтың кілті.', answers: ['Білім'],
      translation: { texts: { '___ — болашақтың кілті.': '___ — ключ к будущему.', Білім: 'Образование' } } },
    { id: 'm', type: 'match', prompt: 'Сөздерді сәйкестендіріңіз.', pairs: [{ word: 'Өнер', translation: 'искусство' }, { word: 'Білім', translation: 'образование' }] },
    { id: 'b', type: 'boolean', prompt: 'Білім маңызды.', answer: true,
      translation: { texts: { 'Білім маңызды.': 'Образование важно.' } } },
    { id: 'o', type: 'order', prompt: 'Сөздерді реттеңіз.', words: ['Білім', 'маңызды.'],
      translation: { texts: { 'Сөздерді реттеңіз.': 'Расставьте слова по порядку.', Білім: 'Образование', 'маңызды.': 'важно' } } },
    { id: 's', type: 'order', orderMode: 'sentences', prompt: 'Сөйлемдерді реттеңіз.', words: ['Сабақ басталды.', 'Оқушылар мәтінді оқыды.'],
      translation: { texts: { 'Сабақ басталды.': 'Урок начался.', 'Оқушылар мәтінді оқыды.': 'Ученики прочитали текст.' } } },
    { id: 'r', type: 'review', prompt: 'Аудармасын жазыңыз.', cards: [{ word: 'Білім', translation: 'образование' }] },
  ]
  const cards = await openExercises(page, exercises)
  for (const card of await cards.all()) await translate(card).click()
  const [choice, fill, match, truth, order, sentences, review] = await cards.all()
  await expect(choice.getByText('Прочитайте текст.')).toBeVisible()
  await expect(choice.getByText('Искусство', { exact: true })).toBeVisible()
  await choice.getByRole('button', { name: 'Өнер', exact: true }).click()
  const unknown = page.getByRole('dialog', { name: 'Өнер' })
  await expect(unknown.getByText('Аударма қолжетімсіз')).toBeVisible()
  await expect(choice.getByRole('radio', { name: 'Өнер' })).not.toBeChecked()
  await unknown.getByRole('button', { name: 'Жабу' }).click()
  await choice.getByRole('radio', { name: 'Білім' }).check()
  await expect(fill.getByText('___ — ключ к будущему.')).toBeVisible()
  await fill.getByRole('textbox').fill('Білім')
  await expect(match.locator('.match-row .exercise-translation')).toHaveText(['искусство', 'образование'])
  await match.getByRole('combobox').first().selectOption('искусство')
  await match.getByRole('combobox').last().selectOption('образование')
  await expect(truth.getByText('Неверно', { exact: true })).toBeVisible()
  await truth.getByRole('radio', { name: 'Дұрыс', exact: true }).check()
  await expect(order.getByText('Образование', { exact: true })).toBeVisible()
  await order.getByRole('button', { name: 'Қосу: Білім', exact: true }).click()
  await order.getByRole('button', { name: 'Қосу: маңызды.', exact: true }).click()
  await expect(sentences.getByText('Урок начался.')).toBeVisible()
  await sentences.getByRole('button', { name: 'Қосу: Сабақ басталды.', exact: true }).click()
  await sentences.getByRole('button', { name: 'Қосу: Оқушылар мәтінді оқыды.', exact: true }).click()
  await expect(review.getByText('образование', { exact: true })).toBeVisible()
  await review.getByRole('textbox').fill('образование')
  for (const card of await cards.all()) {
    await check(card).click()
    await expect(card.locator('.feedback-summary')).toHaveClass(/success/)
  }
})

test('migrates existing lessons and preserves scores when a teacher edits a translation', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Мұғалім ретінде кіру/ }).click()
  await expect(page).toHaveURL(/#\/teach$/)
  await page.evaluate(() => {
    const key = 'alas.learning.v1'
    const data = JSON.parse(localStorage.getItem(key)!)
    data.seedRevision = 5
    const lesson = data.lessons[0]
    for (const exercise of lesson.exercises) delete exercise.translation
    const exercise = lesson.exercises[0]
    data.submissions.push({
      id: 'legacy-score', userId: 'narulan', lessonId: lesson.id, exerciseId: exercise.id,
      prompt: exercise.prompt, score: 3, possible: 3, lines: [], createdAt: Date.now(),
    })
    localStorage.setItem(key, JSON.stringify(data))
  })
  await page.goto('/#/teach/lessons/edit/official-style')
  await page.reload()
  const builder = page.locator('.builder-block').filter({ has: page.getByText('Жаттығу 1', { exact: true }) })
  await builder.getByText('Орысша аудармалар мен сөздік', { exact: true }).click()
  const field = builder.getByRole('textbox', { name: 'Ресми немесе бейресми стиль', exact: true })
  await expect(field).toHaveValue('Официально-деловой или неофициальный стиль')
  await field.fill('Официальный или разговорный стиль')
  await page.getByRole('button', { name: 'Сабақты сақтау', exact: true }).click()
  await expect(page).toHaveURL(/\/teach\/lessons\?saved=official-style$/)
  await page.evaluate(() => localStorage.setItem('alas.demo.session.v1', 'narulan'))
  await page.reload()
  const card = (await openPractice(page)).first()
  await expect(card.locator('.feedback-summary')).toContainText('3 / 3')
  await translate(card).click()
  await expect(card.getByText('Официальный или разговорный стиль')).toBeVisible()
})
