import { ref, shallowRef, watch } from 'vue'

export type SpeechLanguage = 'kk' | 'ru'
export type SpeechVoice = 'female' | 'male'
export const speechSpeeds = [0.75, 0.9, 1, 1.25] as const

interface SpeechRequest {
  text: string
  language: SpeechLanguage
  voice: SpeechVoice
  speed: number
}

type Phase = 'loading' | 'playing' | 'ready' | 'error'
type Failure = 'unavailable' | 'invalid_voice' | 'provider_network_error' | 'synthesis_failed' | 'internal_error' | 'rate_limited' | 'timeout' | 'text_too_long'

interface Playback {
  owner: symbol
  phase: Phase
  failure?: Failure
}

const preferencesKey = 'alas.pronunciation.v1'
function loadPreferences(): Pick<SpeechRequest, 'voice' | 'speed'> {
  try {
    const saved = JSON.parse(localStorage.getItem(preferencesKey) ?? '{}')
    return {
      voice: saved.voice === 'male' ? 'male' : 'female',
      speed: speechSpeeds.some(speed => speed === saved.speed) ? saved.speed : 1,
    }
  } catch { return { voice: 'female', speed: 1 } }
}

export const pronunciationPreferences = ref(loadPreferences())
watch(pronunciationPreferences, preferences => {
  try { localStorage.setItem(preferencesKey, JSON.stringify(preferences)) } catch { /* Keep this session's settings. */ }
}, { deep: true, flush: 'sync' })

export function wordSpeechText(text: string) {
  return text.replace(/^[\p{P}\s]+|[\p{P}\s]+$/gu, '')
}

export function sentences(text: string, language: SpeechLanguage): string[] {
  if (typeof Intl.Segmenter === 'function') {
    return Array.from(new Intl.Segmenter(language, { granularity: 'sentence' }).segment(text), item => item.segment)
  }
  return text.match(/[^.!?…]+(?:[.!?…]+[»”’"]*\s*|$)|[.!?…]+/gu) ?? [text]
}

const passageLimit = 12_000

export const playback = shallowRef<Playback>()
interface Session {
  owner: symbol
  controller: AbortController
  url?: string
  clipKey?: string
}

let session: Session | undefined
let player: HTMLAudioElement | undefined
const sessionClips = new Map<string, Blob>()
const sessionCacheBytes = 16 * 1024 * 1024
let cachedBytes = 0
const silentWav = 'data:audio/wav;base64,UklGRiYAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQIAAAAAAA=='

class SpeechError extends Error {
  constructor(readonly reason: Failure) { super(reason) }
}

function audioElement() {
  player ??= new Audio()
  return player
}

function clearMedia(current?: Session) {
  if (player) {
    player.onended = null
    player.onerror = null
    player.pause()
    player.removeAttribute('src')
    player.load()
  }
  if (current?.url) {
    URL.revokeObjectURL(current.url)
    current.url = undefined
  }
}

export function stopSpeech(owner?: symbol) {
  if (owner && playback.value?.owner !== owner) return
  session?.controller.abort()
  clearMedia(session)
  session = undefined
  playback.value = undefined
}

function fail(current: Session, failure: Failure) {
  if (session !== current) return
  stopSpeech(current.owner)
  playback.value = { owner: current.owner, phase: 'error', failure }
}

function evictClip(key: string) {
  const existing = sessionClips.get(key)
  if (existing) {
    cachedBytes -= existing.size
    sessionClips.delete(key)
  }
}

function rememberClip(key: string, clip: Blob) {
  evictClip(key)
  sessionClips.set(key, clip)
  cachedBytes += clip.size
  while (cachedBytes > sessionCacheBytes || sessionClips.size > 64) {
    evictClip(sessionClips.keys().next().value!)
  }
}

async function fetchClip(request: SpeechRequest, signal: AbortSignal) {
  const key = JSON.stringify([request.text.normalize('NFC').trim(), request.language, request.voice, request.speed])
  const cached = sessionClips.get(key)
  if (cached) {
    rememberClip(key, cached)
    return { clip: cached, key }
  }
  const response = await fetch('/api/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    if (response.status === 429) throw new SpeechError('rate_limited')
    if (response.status === 504) throw new SpeechError('timeout')
    if (response.status === 413) throw new SpeechError('text_too_long')
    switch (payload?.error?.code) {
      case 'invalid_voice': throw new SpeechError('invalid_voice')
      case 'provider_network_error': throw new SpeechError('provider_network_error')
      case 'provider_no_audio':
      case 'provider_http_error':
      case 'synthesis_failed': throw new SpeechError('synthesis_failed')
      case 'internal_error': throw new SpeechError('internal_error')
    }
    throw new SpeechError('unavailable')
  }
  if (response.headers.get('Content-Type')?.split(';')[0] !== 'audio/mpeg') throw new SpeechError('unavailable')
  const clip = await response.blob()
  if (!clip.size) throw new SpeechError('unavailable')
  if (response.headers.get('X-Alas-Playback-Cache') === 'session-v1') rememberClip(key, clip)
  return { clip, key }
}

async function playPrepared(current: Session) {
  const audio = audioElement()
  const timeout = window.setTimeout(() => fail(current, 'timeout'), 10_000)
  try {
    await audio.play()
    if (session === current) playback.value = { owner: current.owner, phase: 'playing' }
  } catch (error) {
    if (session !== current) return
    if (error instanceof DOMException && error.name === 'NotAllowedError') {
      playback.value = { owner: current.owner, phase: 'ready' }
    } else {
      if (current.clipKey) evictClip(current.clipKey)
      fail(current, 'unavailable')
    }
  } finally {
    window.clearTimeout(timeout)
  }
}

async function prepareSpeech(current: Session, request: SpeechRequest) {
  playback.value = { owner: current.owner, phase: 'loading' }
  const timeout = window.setTimeout(() => fail(current, 'timeout'), 310_000)
  try {
    const { clip, key } = await fetchClip(request, current.controller.signal)
    if (session !== current) return
    const audio = audioElement()
    audio.onended = () => { if (session === current && audio.ended) stopSpeech(current.owner) }
    audio.onerror = () => {
      if (session !== current || !audio.error) return
      evictClip(key)
      fail(current, 'unavailable')
    }
    current.clipKey = key
    current.url = URL.createObjectURL(clip)
    audio.src = current.url
    void playPrepared(current)
  } catch (error) {
    fail(current, error instanceof SpeechError ? error.reason : 'unavailable')
  } finally {
    window.clearTimeout(timeout)
  }
}

export function toggleSpeech(owner: symbol, request: SpeechRequest) {
  const current = playback.value
  if (current?.owner === owner) {
    if (current.phase === 'loading') return
    if (current.phase === 'playing') { stopSpeech(owner); return }
    if (current.phase === 'ready' && session) {
      playback.value = { owner, phase: 'loading' }
      void playPrepared(session)
      return
    }
  }

  stopSpeech()
  if (Array.from(request.text.normalize('NFC').trim()).length > passageLimit) {
    playback.value = { owner, phase: 'error', failure: 'text_too_long' }
    return
  }
  if (!request.text.trim()) return
  const next = { owner, controller: new AbortController() }
  session = next

  // Give browsers that require a user gesture permission to use this media element.
  const audio = audioElement()
  audio.src = silentWav
  audio.play().catch(() => undefined)
  void prepareSpeech(next, request)
}
