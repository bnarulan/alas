import asyncio
import hashlib
import json
import logging
import os
import re
import tempfile
import time
import unicodedata
from contextlib import aclosing
from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Protocol

import aiohttp
import edge_tts
from filelock import AsyncFileLock, FileLock, Timeout as LockTimeout

from .audio_tempo import restore_tempo
from .mp3 import Mp3Info, inspect_mp3
from .speech_text import sentence_ends, split_for_retry, split_passage

LOGGER = logging.getLogger(__name__)
MAX_TEXT_CHARS = 12_000
MAX_AUDIO_BYTES = 12 * 1024 * 1024
CACHE_VERSION = "edge-mp3-v3"
VOICES = {
    ("kk", "female"): "kk-KZ-AigulNeural",
    ("kk", "male"): "kk-KZ-DauletNeural",
    ("ru", "female"): "ru-RU-SvetlanaNeural",
    ("ru", "male"): "ru-RU-DmitryNeural",
}


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except ValueError:
        value = minimum - 1
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")
    return value


@dataclass(frozen=True)
class Settings:
    cache_dir: Path
    cache_bytes: int = 128 * 1024 * 1024
    cache_seconds: int = 30 * 86400
    concurrency: int = 3
    pending: int = 20
    requests_per_minute: int = 60
    attempt_timeout: int = 10
    request_timeout: int = 26
    passage_timeout: int = 240
    retries: int = 1
    retry_backoff_ms: int = 350

    @classmethod
    def from_env(cls):
        return cls(
            cache_dir=Path(os.environ.get("ALAS_TTS_CACHE_DIR", ".tts-cache")),
            cache_bytes=env_int("ALAS_TTS_CACHE_MB", 128, 2, 2048) * 1024 * 1024,
            cache_seconds=env_int("ALAS_TTS_CACHE_DAYS", 30, 1, 365) * 86400,
            concurrency=env_int("ALAS_TTS_CONCURRENCY", 3, 1, 16),
            pending=env_int("ALAS_TTS_PENDING", 20, 1, 128),
            requests_per_minute=env_int("ALAS_TTS_RATE_LIMIT", 60, 1, 1000),
            attempt_timeout=env_int("ALAS_TTS_ATTEMPT_TIMEOUT", 10, 1, 30),
            request_timeout=env_int("ALAS_TTS_REQUEST_TIMEOUT", 26, 1, 30),
            passage_timeout=env_int("ALAS_TTS_PASSAGE_TIMEOUT", 240, 30, 300),
            retries=env_int("ALAS_TTS_RETRIES", 1, 0, 2),
            retry_backoff_ms=env_int("ALAS_TTS_RETRY_BACKOFF_MS", 350, 0, 3000),
        )


@dataclass(frozen=True)
class Phrase:
    text: str
    language: str
    voice: str
    rate: str

    def key(self) -> str:
        parts = [CACHE_VERSION, self.text, self.language, self.voice, self.rate]
        if self.language == "kk" and any(len(sentence_ends(chunk)) > 1 for chunk in split_passage(self.text)):
            # Earlier v3 entries checked the final words of each chunk only.
            parts.append("all-sentence-endings")
        return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode("utf-8")).hexdigest()


class InvalidVoice(ValueError):
    pass


def parse_phrase(data: object) -> Phrase:
    if not isinstance(data, dict) or data.keys() - {"text", "language", "voice", "speed"}:
        raise ValueError("Expected a JSON object with text, language, voice and speed.")
    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Text is required.")
    text = unicodedata.normalize("NFC", text.strip())
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"Text must contain at most {MAX_TEXT_CHARS} characters.")
    if any(unicodedata.category(char) in {"Cc", "Cs"} and char not in "\r\n\t" for char in text):
        raise ValueError("Text contains unsupported characters.")
    if not any(char.isalnum() for char in text):
        raise ValueError("Text must include letters or numbers.")
    language = data.get("language")
    if language not in ("kk", "ru"):
        raise ValueError("Language must be kk or ru.")
    voice = data.get("voice", "female")
    if voice not in ("female", "male"):
        raise InvalidVoice("Voice must be female or male.")
    speed = data.get("speed", 1)
    if type(speed) not in (int, float) or not 0.75 <= speed <= 1.25:
        raise ValueError("Speed must be a number from 0.75 to 1.25.")
    percent = ((Decimal(str(speed)) - 1) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return Phrase(text, language, VOICES[language, voice], f"{int(percent):+d}%")


class ProviderFailure(Exception):
    retryable = True


class ProviderNoAudio(ProviderFailure):
    pass


class ProviderNetworkError(ProviderFailure):
    pass


class ProviderHttpError(ProviderFailure):
    def __init__(self, status: int):
        super().__init__(f"Edge returned HTTP {status}")
        self.retryable = status == 429 or status >= 500


class CompressedSpeech(ProviderFailure):
    pass


class Busy(Exception):
    pass


class SpeechProvider(Protocol):
    async def synthesize(self, phrase: Phrase, *, recover_no_audio: bool = False) -> bytes: ...


class EdgeProvider:
    async def synthesize(self, phrase: Phrase, *, recover_no_audio: bool = False) -> bytes:
        requested_rate = int(phrase.rate[:-1])
        if recover_no_audio and requested_rate < 25:
            # Keep the same text and voice. Edge can drop a turn at ordinary rates
            # that it completes at +25%. Correct the tempo before returning any audio.
            audio = await self._stream(replace(phrase, rate="+25%"))
            return await restore_tempo(audio, (100 + requested_rate) / 125)
        return await self._stream(phrase)

    async def _stream(self, phrase: Phrase) -> bytes:
        audio = bytearray()
        reported_text: list[str] = []
        word_durations: list[int] = []
        last_boundary_end = 0
        # Dmitry can return no audio with word boundaries for otherwise valid Russian text.
        boundary = "SentenceBoundary" if phrase.voice == VOICES["ru", "male"] else "WordBoundary"
        try:
            speech = edge_tts.Communicate(phrase.text, phrase.voice, rate=phrase.rate, boundary=boundary)
            async with aclosing(speech.stream()) as stream:
                async for chunk in stream:
                    if chunk["type"] == "audio":
                        audio.extend(chunk["data"])
                        if len(audio) > MAX_AUDIO_BYTES:
                            raise ProviderFailure("audio limit exceeded")
                    elif chunk["type"] == boundary:
                        reported_text.append(chunk["text"])
                        word_durations.append(chunk["duration"])
                        last_boundary_end = max(last_boundary_end, chunk["offset"] + chunk["duration"])
        except edge_tts.exceptions.NoAudioReceived as exc:
            raise ProviderNoAudio("Edge ended synthesis without sending audio") from exc
        except TimeoutError:
            raise
        except aiohttp.ClientResponseError as exc:
            raise ProviderHttpError(exc.status) from exc
        except (edge_tts.exceptions.WebSocketError, aiohttp.ClientConnectionError, OSError) as exc:
            raise ProviderNetworkError("The Edge connection failed") from exc
        except (edge_tts.exceptions.EdgeTTSException, aiohttp.ClientError) as exc:
            raise ProviderFailure("Edge returned an unexpected synthesis response") from exc
        # edge-tts 7.3.1 counts bytes here only when the service sends turn.end.
        # A WebSocket can close cleanly before that event, leaving valid frames but missing speech.
        if speech.state.get("cumulative_audio_bytes") != len(audio):
            raise ProviderNetworkError("Edge stream ended without confirming all audio bytes")
        if not reported_text or spoken_characters("".join(reported_text)) != spoken_characters(phrase.text):
            raise ProviderFailure("Edge did not report boundaries for the complete text")
        data = bytes(audio)
        info = inspect_mp3(data)
        if info is None or last_boundary_end / 10_000_000 > info.seconds + 0.05:
            raise ProviderFailure("Edge audio did not reach the final reported boundary")
        if phrase.language == "kk" and compressed_sentence_ending(phrase, reported_text, word_durations):
            raise CompressedSpeech("Edge compressed the closing words of a sentence")
        return data


def spoken_characters(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFC", text).casefold() if char.isalnum())


def compressed_sentence_ending(phrase: Phrase, words: list[str], durations: list[int]) -> bool:
    # A later sentence can have normal timing even after the preceding ending was compressed.
    endings = {len(spoken_characters(phrase.text[:end])) for end in sentence_ends(phrase.text)}
    speed = 1 + int(phrase.rate[:-1]) / 100
    offset = 0
    short_words = 0
    for i, (word, duration) in enumerate(zip(words, durations)):
        length = len(spoken_characters(word))
        offset += length
        if length >= 3 and duration / 10_000_000 * speed < min(0.16, 0.022 * length):
            short_words += 1
        else:
            short_words = 0
        if offset in endings:
            if i >= 3 and short_words >= 2:
                return True
            short_words = 0
    return False


def atomic_write(path: Path, data: bytes, *, validate_mp3: bool = False) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".write-", delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
            file.close()
            if validate_mp3:
                written = temporary.read_bytes()
                if written != data or inspect_mp3(written) is None:
                    raise OSError("temporary MP3 failed validation after writing")
            os.replace(temporary, path)
        finally:
            file.close()
            temporary.unlink(missing_ok=True)


class AudioCache:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.cache_dir / CACHE_VERSION
        self.locks = self.root / "locks"

    def initialize(self) -> None:
        self.locks.mkdir(parents=True, exist_ok=True)
        self.prune()

    def lookup(self, key: str) -> bytes | None:
        audio_path = self.root / f"{key}.mp3"
        try:
            with audio_path.open("rb") as file:
                info = os.fstat(file.fileno())
                if time.time() - info.st_mtime > self.settings.cache_seconds or info.st_size > MAX_AUDIO_BYTES:
                    return None
                audio = file.read(MAX_AUDIO_BYTES + 1)
            with audio_path.with_suffix(".sha256").open("rb") as digest_file:
                digest = digest_file.read(65)
        except FileNotFoundError:
            return None
        if len(audio) > MAX_AUDIO_BYTES or digest != hashlib.sha256(audio).hexdigest().encode("ascii"):
            return None
        info = inspect_mp3(audio)
        if info is None or not info.standalone:
            return None
        return audio

    def discard_invalid(self, key: str) -> None:
        # Called while the synthesis job holds the key lock and has confirmed a miss.
        path = self.root / f"{key}.mp3"
        if path.exists() or path.with_suffix(".sha256").exists():
            with FileLock(self.locks / "prune.lock", timeout=self.settings.request_timeout):
                self.remove(path)

    def lock(self, key: str, timeout: int) -> AsyncFileLock:
        return AsyncFileLock(str(self.locks / f"{key[:2]}.lock"), timeout=timeout)

    def write(self, key: str, audio: bytes) -> None:
        path = self.root / f"{key}.mp3"
        with FileLock(self.locks / "prune.lock", timeout=self.settings.request_timeout):
            if len(audio) + 64 <= self.settings.cache_bytes:
                atomic_write(path, audio, validate_mp3=True)
                atomic_write(path.with_suffix(".sha256"), hashlib.sha256(audio).hexdigest().encode("ascii"))
            self._prune()

    def prune(self) -> None:
        with FileLock(self.locks / "prune.lock", timeout=self.settings.request_timeout):
            self._prune()

    def _prune(self) -> None:
        now = time.time()
        entries = []
        total = 0
        for path in self.root.glob("*.mp3"):
            if not re.fullmatch(r"[0-9a-f]{64}", path.stem):
                continue
            info = path.stat()
            digest = path.with_suffix(".sha256")
            if now - info.st_mtime > self.settings.cache_seconds or not digest.is_file():
                self.remove(path)
            else:
                size = info.st_size + digest.stat().st_size
                total += size
                entries.append((info.st_mtime, size, path))
        for _, size, path in sorted(entries):
            if total <= self.settings.cache_bytes:
                break
            self.remove(path)
            total -= size
        for path in self.root.glob("*.sha256"):
            if re.fullmatch(r"[0-9a-f]{64}", path.stem) and not path.with_suffix(".mp3").exists():
                path.unlink(missing_ok=True)
        # All writers hold the same lock, so these files only remain after a crash.
        for path in self.root.glob(".write-*"):
            path.unlink(missing_ok=True)

    @staticmethod
    def remove(path: Path) -> None:
        path.with_suffix(".sha256").unlink(missing_ok=True)
        path.unlink(missing_ok=True)


class SpeechService:
    def __init__(self, settings: Settings, provider: SpeechProvider):
        self.settings = settings
        self.provider = provider
        self.cache = AudioCache(settings)
        self.slots = asyncio.Semaphore(settings.concurrency)
        self.jobs: dict[str, asyncio.Task[tuple[bytes, bool]]] = {}

    async def get(self, phrase: Phrase) -> tuple[bytes, bool]:
        key = phrase.key()
        cached = await asyncio.to_thread(self.cache.lookup, key)
        if cached is not None:
            return cached, True
        chunks = split_passage(phrase.text)
        is_passage = len(chunks) > 1 or len(sentence_ends(phrase.text)) > 1
        timeout = self.settings.passage_timeout if is_passage else self.settings.request_timeout
        job = self.jobs.get(key)
        if job is None:
            if len(self.jobs) >= self.settings.pending:
                raise Busy
            job = asyncio.create_task(self._build(key, phrase, chunks, timeout))
            self.jobs[key] = job
            job.add_done_callback(lambda task: self._forget(key, task))
        return await asyncio.wait_for(asyncio.shield(job), timeout=timeout)

    def _forget(self, key: str, task: asyncio.Task) -> None:
        self.jobs.pop(key, None)
        if not task.cancelled():
            task.exception()

    async def _build(self, key: str, phrase: Phrase, chunks: list[str], timeout: int) -> tuple[bytes, bool]:
        try:
            async with self.cache.lock(key, timeout):
                async with asyncio.timeout(timeout):
                    cached = await asyncio.to_thread(self.cache.lookup, key)
                    if cached is not None:
                        return cached, True
                    await asyncio.to_thread(self.cache.discard_invalid, key)
                    audio = await self._synthesize_passage(key, phrase, chunks)
                await asyncio.to_thread(self.cache.write, key, audio)
                return audio, False
        except LockTimeout as exc:
            raise Busy from exc

    async def _synthesize_passage(self, key: str, phrase: Phrase, chunks: list[str]) -> bytes:
        job = key[:12]
        LOGGER.info("TTS %s starting source_chars=%d chunks=%d voice=%s rate=%s", job, len(phrase.text), len(chunks), phrase.voice, phrase.rate)
        frames = 0
        audio_bytes = 0
        profile = None
        parts = []
        for index, text in enumerate(chunks, start=1):
            label = f"{job} chunk={index}/{len(chunks)}"
            for audio, info in await self._render_chunk(replace(phrase, text=text), label, profile):
                profile = info.profile
                frames += info.frames
                audio_bytes += info.end - info.start
                if audio_bytes > MAX_AUDIO_BYTES:
                    raise ProviderFailure("complete passage audio exceeds the audio limit")
                parts.append(audio[info.start:info.end])

        # Edge emits independent CBR MPEG frames. Strip per-clip tags and join only
        # compatible frame streams without seek headers or cross-clip dependencies.
        joined = b"".join(parts)
        combined = await asyncio.to_thread(inspect_mp3, joined)
        if combined is None or combined.frames != frames:
            raise ProviderFailure("combined MP3 failed validation")
        LOGGER.info("TTS %s complete chunks=%d clips=%d bytes=%d seconds=%.3f", job, len(chunks), len(parts), len(joined), combined.seconds)
        return joined

    async def _render_chunk(self, phrase: Phrase, label: str, profile: tuple[int, int, int, int] | None, depth: int = 0) -> list[tuple[bytes, Mp3Info]]:
        try:
            clip = await self._synthesize(phrase, label, profile)
        except (CompressedSpeech, ProviderNoAudio, TimeoutError) as exc:
            limit = 2 if isinstance(exc, CompressedSpeech) or self.settings.retries else 0
            split = split_for_retry(phrase.text) if depth < limit else None
            if split is None:
                raise
            left, right = split
            LOGGER.warning("TTS %s retrying %s as two clauses (%d + %d chars)", label, type(exc).__name__, len(left), len(right))
            first = await self._render_chunk(replace(phrase, text=left), label + ".1", profile, depth + 1)
            second = await self._render_chunk(replace(phrase, text=right), label + ".2", first[0][1].profile, depth + 1)
            return first + second
        LOGGER.info("TTS %s complete chars=%d seconds=%.3f", label, len(phrase.text), clip[1].seconds)
        return [clip]

    async def _synthesize(self, phrase: Phrase, label: str, profile: tuple[int, int, int, int] | None) -> tuple[bytes, Mp3Info]:
        recover_no_audio = False
        for attempt in range(self.settings.retries + 1):
            try:
                async with self.slots:
                    async with asyncio.timeout(self.settings.attempt_timeout):
                        if recover_no_audio and phrase.rate != "+25%":
                            LOGGER.info("TTS %s retrying empty Edge response with tempo recovery", label)
                        audio = await self.provider.synthesize(phrase, recover_no_audio=recover_no_audio)
                if len(audio) <= MAX_AUDIO_BYTES:
                    info = await asyncio.to_thread(inspect_mp3, audio)
                    if info is not None and info.standalone and (profile is None or info.profile == profile):
                        return audio, info
                raise ProviderFailure("invalid or incomplete MP3")
            except CompressedSpeech:
                raise
            except (ProviderFailure, TimeoutError) as exc:
                LOGGER.warning("TTS %s attempt=%d failed (%s)", label, attempt + 1, type(exc).__name__, exc_info=True)
                if attempt == self.settings.retries or (isinstance(exc, ProviderFailure) and not exc.retryable):
                    raise
                recover_no_audio = isinstance(exc, ProviderNoAudio)
                await asyncio.sleep(self.settings.retry_backoff_ms / 1000 * 2 ** attempt)
        raise AssertionError("Unreachable")

    async def close(self) -> None:
        await asyncio.gather(*tuple(self.jobs.values()), return_exceptions=True)
