import { expect, test } from '@playwright/test'
import type { Locator, Page } from '@playwright/test'
import { pronunciationLesson } from '../../src/data/seed'

async function openLesson(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: /Оқушы ретінде кіру/ }).click()
  await expect(page.getByRole('heading', { name: /Бақыт/ })).toBeVisible()
  await page.evaluate(lesson => {
    const key = 'alas.learning.v1'
    const data = JSON.parse(localStorage.getItem(key)!)
    data.lessons.push(lesson)
    localStorage.setItem(key, JSON.stringify(data))
  }, pronunciationLesson)
  await page.goto('/#/learn/lessons/education-and-future')
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Білім және болашақ' })).toBeVisible()
}

function popup(page: Page) { return page.getByRole('dialog', { name: 'Білім' }) }
const speakKk = (within: Locator) => within.getByRole('button', { name: 'Қазақша тыңдау', exact: true })
const speakRu = (within: Locator) => within.getByRole('button', { name: 'Орысша тыңдау', exact: true })

test('plays both popup languages, prevents duplicate clicks and reuses the server cache', async ({ page, isMobile }) => {
  await openLesson(page)
  const token = page.getByRole('button', { name: 'Білім', exact: true })
  if (isMobile) await token.tap()
  else await token.press('Enter')
  const card = popup(page)
  await expect(card.getByText('образование, знания', { exact: true })).toBeVisible()
  const requests: Array<Record<string, unknown>> = []
  await page.route('**/api/tts', async route => {
    requests.push(route.request().postDataJSON())
    await new Promise(resolve => setTimeout(resolve, 160))
    await route.continue()
  })
  const kk = speakKk(card)
  const ru = speakRu(card)
  const first = page.waitForResponse(response => response.url().endsWith('/api/tts'))
  if (isMobile) { await kk.tap(); await kk.dispatchEvent('click') }
  else { await kk.click(); await kk.dispatchEvent('click') }
  await expect(kk).toHaveAttribute('data-state', 'loading')
  const clip = await first
  expect(clip.status()).toBe(200)
  expect(clip.headers()['content-type']).toBe('audio/mpeg')
  await expect(card.locator('.tts-button').first()).toHaveAttribute('data-state', 'playing')
  expect(requests).toEqual([{ text: 'Білім', language: 'kk', voice: 'female', speed: 1 }])

  const second = page.waitForResponse(response => response.url().endsWith('/api/tts'))
  await ru.click()
  await expect(card.locator('.tts-button').first()).toHaveAttribute('data-state', 'idle')
  expect((await second).status()).toBe(200)
  await expect(card.locator('.tts-button').last()).toHaveAttribute('data-state', 'playing')
  expect(requests.at(-1)).toEqual({ text: 'образование, знания', language: 'ru', voice: 'female', speed: 1 })

  const repeat = page.waitForResponse(response => response.url().endsWith('/api/tts'))
  await kk.click()
  expect((await repeat).headers()['x-tts-cache']).toBe('HIT')
  await expect(card.locator('.tts-button').first()).toHaveAttribute('data-state', 'playing')
  await card.getByRole('button', { name: /Дыбыстауды тоқтату.*Қазақша/ }).click()
  await expect(kk).toHaveAttribute('data-state', 'idle')
  await card.getByRole('button', { name: 'Сөздікке қосу' }).click()
  await expect(card.getByRole('button', { name: 'Сөздікте сақталған' })).toBeVisible()
  if (isMobile) await card.getByRole('button', { name: 'Жабу' }).tap()
  else await page.keyboard.press('Escape')
  await expect(card).toHaveCount(0)
})

test('speaks selected sentences and paragraphs with persisted speed and voice', async ({ page }) => {
  await openLesson(page)
  const reader = page.locator('.reading-audio')
  await reader.getByText('Дыбыстау баптаулары', { exact: true }).click()
  await reader.getByLabel('Дыбыстау дауысы').selectOption('male')
  await reader.getByLabel('Оқу жылдамдығы').selectOption('0.9')
  await page.reload()
  await reader.getByText('Дыбыстау баптаулары', { exact: true }).click()
  await expect(reader.getByLabel('Дыбыстау дауысы')).toHaveValue('male')
  await expect(reader.getByLabel('Оқу жылдамдығы')).toHaveValue('0.9')

  await reader.getByLabel('Тыңдайтын үзінді').selectOption('sentence:0')
  let pending = page.waitForRequest(request => request.url().endsWith('/api/tts'))
  await reader.getByRole('button', { name: 'Үзіндіні тыңдау', exact: true }).click()
  expect((await pending).postDataJSON()).toEqual({ text: 'Білім — болашақтың кілті.', language: 'kk', voice: 'male', speed: 0.9 })
  await reader.getByLabel('Дыбыстау тілі').selectOption('ru')
  await reader.getByLabel('Тыңдайтын үзінді').selectOption('paragraph:1')
  await reader.getByLabel('Оқу жылдамдығы').selectOption('1.25')
  pending = page.waitForRequest(request => request.url().endsWith('/api/tts'))
  await reader.getByRole('button', { name: 'Үзіндіні тыңдау', exact: true }).click()
  expect((await pending).postDataJSON()).toEqual({ text: 'Искусство развивает воображение. Надежда придаёт нам сил.', language: 'ru', voice: 'male', speed: 1.25 })
  await expect(reader.locator('.tts-button')).toHaveAttribute('data-state', 'playing')
})

test('retries after a failed request and keeps the vocabulary card on the same side', async ({ page }) => {
  await openLesson(page)
  await page.getByRole('button', { name: 'Білім', exact: true }).click()
  await popup(page).getByRole('button', { name: 'Сөздікке қосу' }).click()
  await popup(page).getByRole('button', { name: 'Жабу' }).click()
  await page.goto('/#/learn/vocabulary')
  const flash = page.locator('.flash-panel')
  const flip = flash.locator('.flashcard')
  await expect(flip).toHaveAttribute('aria-pressed', 'false')
  await expect(flip).toContainText('білім')
  await page.route('**/api/tts', route => route.abort(), { times: 1 })
  await speakKk(flash).click()
  await expect(flash.getByText('Дыбысты ойнату мүмкін болмады. Қайталап көріңіз.')).toBeVisible()
  await page.route('**/api/tts', route => route.fulfill({
    status: 503, json: { error: { code: 'provider_no_audio' } },
  }), { times: 1 })
  await speakKk(flash).click()
  await expect(flash.getByText('Дыбыстау қызметі аудио дайындай алмады. Қайталап көріңіз.')).toBeVisible()
  await speakKk(flash).click()
  await expect(flash.locator('.tts-button').first()).toHaveAttribute('data-state', 'playing')
  await expect(flip).toHaveAttribute('aria-pressed', 'false')
  await speakRu(flash).click()
  await expect(flash.locator('.tts-button').last()).toHaveAttribute('data-state', 'playing')
  await expect(flip).toHaveAttribute('aria-pressed', 'false')
  await flip.click()
  await expect(flip).toContainText('образование, знания')
})

test('requires a second gesture only when the browser blocks asynchronous playback', async ({ page }) => {
  await page.addInitScript(() => {
    const play = HTMLMediaElement.prototype.play
    let blocked = false
    HTMLMediaElement.prototype.play = function () {
      if (!blocked && this.src.startsWith('blob:')) {
        blocked = true
        return Promise.reject(new DOMException('Gesture required', 'NotAllowedError'))
      }
      return play.call(this)
    }
  })
  await openLesson(page)
  await page.getByRole('button', { name: 'Білім', exact: true }).click()
  const kk = speakKk(popup(page))
  let requests = 0
  page.on('request', request => { if (request.url().endsWith('/api/tts')) requests++ })
  await kk.click()
  await expect(kk).toHaveAttribute('data-state', 'ready')
  await kk.click()
  await expect(popup(page).locator('.tts-button').first()).toHaveAttribute('data-state', 'playing')
  expect(requests).toBe(1)
})

test('sends the full passage once and plays the combined MP3', async ({ page }) => {
  await openLesson(page)
  const passage = 'Білім — болашақтың кілті. '.repeat(55) + 'Үміт бізге күш береді.'
  await page.evaluate(text => {
    const key = 'alas.learning.v1'
    const data = JSON.parse(localStorage.getItem(key)!)
    const lesson = data.lessons.find((item: { id: string }) => item.id === 'education-and-future')
    lesson.text = text
    localStorage.setItem(key, JSON.stringify(data))
  }, passage)
  await page.reload()
  const sent: string[] = []
  page.on('request', request => { if (request.url().endsWith('/api/tts')) sent.push(request.postDataJSON().text) })
  const reader = page.locator('.reading-audio')
  const pending = page.waitForResponse(response => response.url().endsWith('/api/tts'))
  await reader.getByRole('button', { name: 'Үзіндіні тыңдау', exact: true }).click()
  const audio = await pending
  expect(audio.status()).toBe(200)
  expect(audio.headers()['content-type']).toBe('audio/mpeg')
  // The fixture returns 8640 bytes per provider call. The passage must contain several clips.
  expect(Number(audio.headers()['content-length'])).toBeGreaterThan(8640 * 3)
  expect(sent).toEqual([passage])
  await expect(reader.locator('.tts-button')).toHaveAttribute('data-state', 'playing')
  await expect(reader.locator('.tts-button')).toHaveAttribute('data-state', 'idle', { timeout: 15_000 })
  expect(sent).toEqual([passage])
})
