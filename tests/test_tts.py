import asyncio
import hashlib
import json
import os
import time
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import aiohttp
import edge_tts
from aiohttp.test_utils import TestClient, TestServer

from backend.app import create_app
from backend.audio_tempo import restore_tempo
from backend.mp3 import inspect_mp3
from backend.speech_text import CHUNK_CHARS, split_for_retry, split_passage
from backend.tts import (
    CACHE_VERSION, MAX_TEXT_CHARS, CompressedSpeech, EdgeProvider, Phrase, ProviderFailure, ProviderHttpError,
    ProviderNetworkError, ProviderNoAudio, Settings, parse_phrase,
)
from tests.audio_fixture import FRAME, SILENT_MP3


class FakeProvider:
    def __init__(self):
        self.calls = []
        self.active = 0
        self.peak = 0
        self.failures = []
        self.audio = SILENT_MP3
        self.pause = 0.03

    async def synthesize(self, phrase: Phrase, *, recover_no_audio: bool = False):
        self.calls.append(phrase)
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            await asyncio.sleep(self.pause)
            if self.failures:
                raise self.failures.pop(0)
            return self.audio
        finally:
            self.active -= 1


class ValidationTests(unittest.TestCase):
    def test_unicode_languages_voices_and_speed(self):
        cases = [
            ("Білім", "kk", "female", 1, "kk-KZ-AigulNeural", "+0%"),
            ("Әңгіме", "kk", "male", 0.75, "kk-KZ-DauletNeural", "-25%"),
            ("Қазақ", "kk", "female", 0.9, "kk-KZ-AigulNeural", "-10%"),
            ("Өнер", "kk", "female", 1.25, "kk-KZ-AigulNeural", "+25%"),
            ("Үміт", "kk", "male", 1, "kk-KZ-DauletNeural", "+0%"),
            ("Ә ә Ғ ғ Қ қ Ң ң Ө ө Ұ ұ Ү ү Һ һ І і", "kk", "female", 1, "kk-KZ-AigulNeural", "+0%"),
            ("Білім — болашақтың кілті.", "kk", "female", 1, "kk-KZ-AigulNeural", "+0%"),
            ("Образование", "ru", "female", 1, "ru-RU-SvetlanaNeural", "+0%"),
            ("Добро пожаловать на платформу Alaś.", "ru", "male", 1.25, "ru-RU-DmitryNeural", "+25%"),
        ]
        for text, language, voice, speed, approved, rate in cases:
            with self.subTest(text=text, voice=voice):
                self.assertEqual(parse_phrase(dict(text=text, language=language, voice=voice, speed=speed)),
                                 Phrase(text, language, approved, rate))

    def test_cache_key_normalization_and_isolation(self):
        base = {"text": "  Алаs\u0301: қарым-қатынас және O’Neil. \n", "language": "kk"}
        normal = parse_phrase(base)
        self.assertEqual(normal.text, "Алаś: қарым-қатынас және O’Neil.")
        self.assertEqual(normal.key(), parse_phrase({**base, "text": normal.text}).key())
        for change in ({"language": "ru"}, {"voice": "male"}, {"speed": 0.9}, {"text": normal.text.lower()}):
            self.assertNotEqual(normal.key(), parse_phrase({**base, **change}).key())
        with patch("backend.tts.CACHE_VERSION", "other-format"):
            other_key = normal.key()
        self.assertNotEqual(other_key, normal.key())

    def test_cache_rekeys_only_kazakh_clips_with_previously_unchecked_sentence_endings(self):
        for text, language, rekeyed in [
            ("Білім", "kk", False),
            ("Білім — болашақтың кілті. Өнер мәңгі.", "kk", True),
            ("Первое предложение. Второе предложение.", "ru", False),
        ]:
            phrase = parse_phrase({"text": text, "language": language})
            previous = [CACHE_VERSION, phrase.text, phrase.language, phrase.voice, phrase.rate]
            old_key = hashlib.sha256(json.dumps(previous, ensure_ascii=False).encode("utf-8")).hexdigest()
            self.assertEqual(phrase.key() != old_key, rekeyed)

    def test_mp3_length_and_header_validation(self):
        info = inspect_mp3(SILENT_MP3)
        self.assertTrue(info.standalone)
        self.assertEqual(info.seconds, 1.44)
        self.assertIsNone(inspect_mp3(SILENT_MP3[:-1]))
        self.assertIsNone(inspect_mp3(b"ID3invalid" + SILENT_MP3))
        self.assertIsNone(inspect_mp3(b""))
        self.assertFalse(inspect_mp3(FRAME[:4] + b"\x01" + FRAME[5:]).standalone)

    def test_passage_split_preserves_unicode_and_punctuation(self):
        paragraph = " «Қазақ тілін үйренеміз!» Әңгіме, қиял — өнер. " * 20
        text = paragraph + "\r\n\r\n" + "Ұ, Ү, Ғ, Ң, Һ және І." * 35 + "\nҚорытынды сөйлем."
        chunks = split_passage(text)
        self.assertGreater(len(chunks), 2)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(len(chunk) <= CHUNK_CHARS for chunk in chunks))
        unpunctuated = "Қазақша сөздер " * 34
        self.assertEqual("".join(split_passage(unpunctuated)), unpunctuated)
        self.assertTrue(split_passage(unpunctuated)[0].endswith(" "))


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_stream_recovery_preserves_voice_words_and_corrects_tempo(self):
        text = "Добро пожаловать на платформу Alaś."
        phrase = parse_phrase({"text": text, "language": "ru", "voice": "male", "speed": 1})
        provider = EdgeProvider()
        with patch.object(provider, "_stream", return_value=SILENT_MP3) as stream:
            recovered = await provider.synthesize(phrase, recover_no_audio=True)
        stream.assert_awaited_once_with(replace(phrase, rate="+25%"))
        info = inspect_mp3(recovered)
        self.assertTrue(info.standalone)
        self.assertEqual(info.profile, inspect_mp3(SILENT_MP3).profile)
        self.assertAlmostEqual(info.seconds, 1.8, delta=0.15)

    async def test_tempo_conversion_refuses_a_truncated_source(self):
        with self.assertRaises(ValueError):
            await restore_tempo(SILENT_MP3[:-1], 0.8)

    async def edge_stream(self, words, confirmed, audio_length=2, *, text="Өнер мәңгі.", language="kk", durations=None):
        calls = []

        class Communicate:
            def __init__(self, text, voice, rate, boundary):
                self.state = {"cumulative_audio_bytes": 0}
                self.boundary = boundary
                calls.append((text, voice, rate, boundary))

            async def stream(self):
                offset = 0
                for word, duration in zip(words, durations if durations is not None else [100_000] * len(words)):
                    yield {"type": self.boundary, "text": word, "offset": offset, "duration": duration}
                    offset += duration
                for _ in range(audio_length):
                    yield {"type": "audio", "data": FRAME}
                if confirmed:
                    self.state["cumulative_audio_bytes"] = len(FRAME) * audio_length

        phrase = parse_phrase({"text": text, "language": language, "voice": "male", "speed": 0.9})
        with patch("backend.tts.edge_tts.Communicate", Communicate):
            audio = await EdgeProvider().synthesize(phrase)
        return audio, calls

    async def test_edge_adapter_drains_the_stream_and_uses_the_approved_voice(self):
        audio, calls = await self.edge_stream(["Өнер", "мәңгі"], confirmed=True)
        self.assertEqual(audio, FRAME * 2)
        self.assertEqual(calls, [("Өнер мәңгі.", "kk-KZ-DauletNeural", "-10%", "WordBoundary")])

    async def test_dmitry_uses_complete_sentence_metadata(self):
        text = "Образование — ключ к будущему."
        audio, calls = await self.edge_stream([text], confirmed=True, text=text, language="ru")
        self.assertEqual(audio, FRAME * 2)
        self.assertEqual(calls, [(text, "ru-RU-DmitryNeural", "-10%", "SentenceBoundary")])

    async def test_edge_rejects_a_clean_close_without_turn_end(self):
        with self.assertRaisesRegex(ProviderFailure, "without confirming"):
            await self.edge_stream(["Өнер", "мәңгі"], confirmed=False)

    async def test_edge_rejects_a_completed_stream_missing_the_final_word(self):
        with self.assertRaisesRegex(ProviderFailure, "complete text"):
            await self.edge_stream(["Өнер"], confirmed=True)

    async def test_edge_rejects_phantom_closing_words_even_after_turn_end(self):
        words = ["баяндамалар", "осы", "стильде", "жазылады"]
        with self.assertRaises(CompressedSpeech):
            await self.edge_stream(words, confirmed=True, text=" ".join(words) + ".")

    async def test_normal_final_sentence_does_not_hide_a_compressed_earlier_ending(self):
        text = "Баяндамалар осы стильде жазылады. Өнер мәңгі."
        durations = [3_000_000, 2_000_000, 200_000, 0, 2_500_000, 2_500_000]
        with self.assertRaises(CompressedSpeech):
            await self.edge_stream(text.replace(".", "").split(), True, 60, text=text, durations=durations)

    async def test_edge_preserves_underlying_exception_and_distinguishes_failure_types(self):
        phrase = parse_phrase({"text": "Білім", "language": "kk"})
        for original, expected in [
            (edge_tts.exceptions.NoAudioReceived("empty stream"), ProviderNoAudio),
            (edge_tts.exceptions.WebSocketError("socket closed"), ProviderNetworkError),
            (aiohttp.ServerDisconnectedError(), ProviderNetworkError),
            (edge_tts.exceptions.UnexpectedResponse("invalid metadata"), ProviderFailure),
        ]:
            with self.subTest(original=type(original).__name__):
                with patch("backend.tts.edge_tts.Communicate", side_effect=original):
                    with self.assertRaises(expected) as result:
                        await EdgeProvider().synthesize(phrase)
                self.assertIs(type(result.exception), expected)
                self.assertIs(result.exception.__cause__, original)

    async def test_aiohttp_timeout_is_not_reported_as_a_network_failure(self):
        phrase = parse_phrase({"text": "Білім", "language": "kk"})
        with patch("backend.tts.edge_tts.Communicate", side_effect=aiohttp.ServerTimeoutError()):
            with self.assertRaises(TimeoutError):
                await EdgeProvider().synthesize(phrase)


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        cache = TemporaryDirectory()
        self.addCleanup(cache.cleanup)
        self.settings = Settings(cache_dir=Path(cache.name))
        self.provider = FakeProvider()

    async def client(self, settings=None, provider=None):
        client = TestClient(TestServer(create_app(settings or self.settings, provider or self.provider)))
        self.addAsyncCleanup(client.close)
        await client.start_server()
        return client

    async def post(self, client, **values):
        return await client.post("/api/tts", json={"text": "Білім", "language": "kk", **values})

    async def test_valid_audio_is_reused_across_requests_and_restarts(self):
        client = await self.client()
        first = await self.post(client)
        self.assertEqual((first.status, first.content_type, first.headers["X-TTS-Cache"]), (200, "audio/mpeg", "MISS"))
        self.assertEqual(await first.read(), SILENT_MP3)
        repeat = await self.post(client, text="  Білім ")
        self.assertEqual(repeat.headers["X-TTS-Cache"], "HIT")
        await client.close()

        new_provider = FakeProvider()
        restarted = await self.client(provider=new_provider)
        cached = await self.post(restarted)
        self.assertEqual(cached.headers["X-TTS-Cache"], "HIT")
        self.assertEqual(await cached.read(), SILENT_MP3)
        self.assertEqual(new_provider.calls, [])

    async def test_duplicate_concurrent_requests_across_two_app_instances(self):
        client = await self.client()
        second_worker = await self.client()
        requests = [self.post(worker) for worker in (client, second_worker) * 4]
        results = await asyncio.gather(*requests)
        self.assertEqual([item.status for item in results], [200] * len(results))
        self.assertEqual(len(self.provider.calls), 1)

    async def test_concurrency_is_bounded(self):
        client = await self.client(replace(self.settings, concurrency=2))
        results = await asyncio.gather(*(self.post(client, text=f"Білім {i}") for i in range(8)))
        self.assertEqual([response.status for response in results], [200] * len(results))
        self.assertEqual(self.provider.peak, 2)

    async def test_pending_limit_returns_a_safe_busy_error(self):
        self.provider.pause = 0.2
        client = await self.client(replace(self.settings, pending=1))
        first = asyncio.create_task(self.post(client))
        while not self.provider.calls:
            await asyncio.sleep(0.005)
        busy = await self.post(client, text="Өнер")
        self.assertEqual(busy.status, 503)
        self.assertEqual((await busy.json())["error"]["code"], "busy")
        self.assertEqual((await first).status, 200)

    async def test_truncated_cache_entry_is_regenerated(self):
        client = await self.client()
        self.assertEqual((await self.post(client)).status, 200)
        audio_path = next(self.settings.cache_dir.rglob("*.mp3"))
        # Truncation on a frame boundary would otherwise look like a valid shorter clip.
        audio_path.write_bytes(SILENT_MP3[:-len(FRAME)])
        regenerated = await self.post(client)
        self.assertEqual(regenerated.headers["X-TTS-Cache"], "MISS")
        self.assertEqual(await regenerated.read(), SILENT_MP3)
        self.assertEqual(len(self.provider.calls), 2)

    async def test_a_valid_looking_v1_prefix_is_never_served(self):
        previous = self.settings.cache_dir / "edge-mp3-v1"
        previous.mkdir()
        phrase = parse_phrase({"text": "Білім", "language": "kk"})
        with patch("backend.tts.CACHE_VERSION", previous.name):
            old_mp3 = previous / (phrase.key() + ".mp3")
        old_mp3.write_bytes(FRAME)
        old_mp3.with_suffix(".sha256").write_text(hashlib.sha256(FRAME).hexdigest(), "ascii")

        client = await self.client()
        result = await self.post(client)
        self.assertEqual(result.headers["X-TTS-Cache"], "MISS")
        self.assertEqual(await result.read(), SILENT_MP3)
        self.assertEqual(len(self.provider.calls), 1)

    async def test_corrupt_mp3_with_matching_digest_is_evicted_even_if_regeneration_fails(self):
        client = await self.client(replace(self.settings, retries=0))
        result = await self.post(client)
        self.assertEqual(result.status, 200)
        path = next(self.settings.cache_dir.rglob("*.mp3"))
        corrupt = SILENT_MP3[:-1]
        path.write_bytes(corrupt)
        path.with_suffix(".sha256").write_text(hashlib.sha256(corrupt).hexdigest(), "ascii")

        self.provider.failures.append(ProviderNoAudio("empty response"))
        result = await self.post(client)
        self.assertEqual(result.status, 503)
        self.assertEqual((await result.json())["error"]["code"], "provider_no_audio")
        self.assertFalse(path.exists())
        self.assertFalse(path.with_suffix(".sha256").exists())

    async def test_cache_respects_retention_and_size_limits(self):
        client = await self.client(replace(self.settings, cache_seconds=60, cache_bytes=len(SILENT_MP3) + 64))
        self.assertEqual((await self.post(client)).status, 200)
        audio_path = next(self.settings.cache_dir.rglob("*.mp3"))
        old = time.time() - 120
        os.utime(audio_path, (old, old))
        aged = await self.post(client)
        self.assertEqual(aged.headers["X-TTS-Cache"], "MISS")
        self.assertEqual(len(self.provider.calls), 2)

        newest = await self.post(client, text="Үміт")
        self.assertEqual(newest.status, 200)
        self.assertFalse(audio_path.exists())
        self.assertEqual(len(list(self.settings.cache_dir.rglob("*.mp3"))), 1)

    async def test_invalid_requests_are_safe(self):
        client = await self.client()
        invalid = [
            {"text": ""}, {"text": " ? "}, {"text": "А" * (MAX_TEXT_CHARS + 1)}, {"text": 4}, {"text": "\0Білім"},
            {"text": "x\ud800"}, {"language": "en"}, {"language": []},
            {"speed": True}, {"speed": "1"}, {"speed": 0.74}, {"speed": 1.26}, {"other": "field"},
        ]
        for change in invalid:
            with self.subTest(change=change):
                response = await self.post(client, **change)
                self.assertEqual(response.status, 400)
                self.assertEqual((await response.json())["error"]["code"], "invalid_input")
        for voice in ("en-US-GuyNeural", {}, None):
            response = await self.post(client, voice=voice)
            self.assertEqual(response.status, 400)
            self.assertEqual((await response.json())["error"]["code"], "invalid_voice")
        malformed = await client.post("/api/tts", data=b"{", headers={"Content-Type": "application/json"})
        self.assertEqual(malformed.status, 400)
        too_large = await client.post("/api/tts", data=json.dumps({"text": "a" * (MAX_TEXT_CHARS * 12 + 2048)}), headers={"Content-Type": "application/json"})
        self.assertEqual(too_large.status, 413)
        self.assertEqual((await client.post("/api/tts", data="Білім")).status, 415)
        self.assertFalse(self.provider.calls)

    async def test_retry_recovers_a_transient_provider_failure(self):
        self.provider.failures.append(ProviderFailure("private network details"))
        client = await self.client()
        response = await self.post(client)
        self.assertEqual(response.status, 200)
        self.assertEqual(await response.read(), SILENT_MP3)
        self.assertEqual(len(self.provider.calls), 2)

    async def test_full_passage_retries_the_failed_chunk_and_caches_one_ordered_mp3(self):
        passage = " ".join(f"{i} — Әділдік пен білім өмірдің негізі." for i in range(42)) + " Қорытынды сөз."
        chunks = split_passage(passage)
        self.assertGreater(len(chunks), 3)
        self.assertGreater(len(passage), 1000)
        provider = FakeProvider()
        calls = []

        async def synthesize(phrase, *, recover_no_audio=False):
            calls.append(phrase.text)
            if len(calls) == 2:
                raise ProviderFailure("temporary clip failure")
            # Leave a distinct byte in each frame so a swapped chunk breaks the test.
            return FRAME[:-1] + bytes([chunks.index(phrase.text)])

        provider.synthesize = synthesize
        client = await self.client(provider=provider)
        result = await self.post(client, text=passage)
        self.assertEqual(result.status, 200)
        self.assertEqual(calls, [chunks[0], chunks[1], *chunks[1:]])
        expected = b"".join(FRAME[:-1] + bytes([i]) for i in range(len(chunks)))
        self.assertEqual(await result.read(), expected)
        self.assertTrue(inspect_mp3(expected).standalone)
        self.assertEqual(len(list(self.settings.cache_dir.rglob("*.mp3"))), 1)
        hit = await self.post(client, text=passage)
        self.assertEqual(hit.headers["X-TTS-Cache"], "HIT")
        self.assertEqual(await hit.read(), expected)

    async def test_failed_final_chunk_never_returns_or_caches_a_prefix(self):
        passage = "Әңгіме, қиял — өнер. " * 40 + "Қорытынды сөз."
        chunks = split_passage(passage)
        calls = []

        async def synthesize(phrase, *, recover_no_audio=False):
            calls.append(phrase.text)
            if phrase.text == chunks[-1]:
                return SILENT_MP3[:-1]
            return SILENT_MP3

        self.provider.synthesize = synthesize
        client = await self.client()
        result = await self.post(client, text=passage)
        self.assertEqual(result.status, 502)
        self.assertEqual((await result.json())["error"]["code"], "synthesis_failed")
        self.assertEqual(calls, [*chunks, chunks[-1]])
        self.assertFalse(list(self.settings.cache_dir.rglob("*.mp3")))

    async def test_compressed_final_clause_is_regenerated_without_publishing_the_failed_take(self):
        text = "Заң, бұйрық, қаулы, нұсқаулықтар, хабарландырулар, іскерлік хаттардың түрлері, баяндамалар осы стильде жазылады."
        left, right = split_for_retry(text)
        self.assertTrue(left.endswith("хабарландырулар, "))
        self.assertEqual(left + right, text)
        calls = []

        async def synthesize(phrase, *, recover_no_audio=False):
            calls.append(phrase.text)
            if phrase.text == text:
                raise CompressedSpeech("Edge compressed the ending")
            return FRAME * (1 if phrase.text == left else 2)

        self.provider.synthesize = synthesize
        client = await self.client()
        result = await self.post(client, text=text)
        self.assertEqual(result.status, 200)
        self.assertEqual(calls, [text, left, right])
        self.assertEqual(await result.read(), FRAME * 3)

    async def test_empty_passage_retries_with_recovery_then_synthesizes_both_clauses(self):
        passage = "Добро пожаловать на платформу Alaś. Образование — ключ к будущему."
        left, right = split_for_retry(passage)
        self.assertEqual(left + right, passage)
        calls = []

        async def synthesize(phrase, *, recover_no_audio=False):
            calls.append((phrase.text, recover_no_audio))
            if phrase.text == passage:
                raise ProviderNoAudio("Edge closed the turn")
            return FRAME * (1 if phrase.text == left else 2)

        self.provider.synthesize = synthesize
        client = await self.client(replace(self.settings, retry_backoff_ms=0))
        response = await self.post(client, language="ru", voice="male", text=passage)
        self.assertEqual(response.status, 200)
        self.assertEqual(await response.read(), FRAME * 3)
        self.assertEqual(calls, [(passage, False), (passage, True), (left, False), (right, False)])
        cached = await self.post(client, language="ru", voice="male", text=passage)
        self.assertEqual(cached.headers["X-TTS-Cache"], "HIT")
        self.assertEqual(await cached.read(), FRAME * 3)

    async def test_no_audio_does_not_mislabel_a_supported_voice_or_leak_provider_error(self):
        self.provider.failures = [ProviderNoAudio("private details")] * 2
        client = await self.client()
        with self.assertLogs("backend.tts", level="WARNING") as captured:
            response = await self.post(client, voice="male")
        self.assertEqual(response.status, 503)
        self.assertEqual((await response.json())["error"]["code"], "provider_no_audio")
        self.assertNotIn("private", await response.text())
        self.assertTrue(all(record.exc_info[0] is ProviderNoAudio for record in captured.records))
        self.assertEqual([item.voice for item in self.provider.calls], ["kk-KZ-DauletNeural"] * 2)
        self.assertFalse(list(self.settings.cache_dir.rglob("*.mp3")))

    async def test_network_rejections_and_internal_failures_have_distinct_codes(self):
        client = await self.client(replace(self.settings, retries=0))
        cases = [
            (ProviderNetworkError("connection reset"), 502, "provider_network_error"),
            (ProviderHttpError(403), 502, "provider_http_error"),
            (ProviderHttpError(429), 503, "provider_http_error"),
            (RuntimeError("private details"), 500, "internal_error"),
        ]
        for failure, status, code in cases:
            self.provider.failures = [failure]
            with self.assertLogs("backend", level="WARNING") as captured:
                response = await self.post(client)
            self.assertEqual(response.status, status)
            self.assertEqual((await response.json())["error"]["code"], code)
            self.assertNotIn(str(failure), await response.text())
            self.assertTrue(any(record.exc_info and record.exc_info[0] is type(failure) for record in captured.records))

    async def test_non_retryable_provider_rejection_is_attempted_once(self):
        client = await self.client()
        self.provider.failures = [ProviderHttpError(403)]
        response = await self.post(client)
        self.assertEqual(response.status, 502)
        self.assertEqual(len(self.provider.calls), 1)

    async def test_invalid_provider_audio_is_never_cached(self):
        self.provider.audio = SILENT_MP3[:-1]
        client = await self.client(replace(self.settings, retries=0))
        response = await self.post(client)
        self.assertEqual(response.status, 502)
        self.assertEqual((await response.json())["error"]["code"], "synthesis_failed")
        self.assertFalse(list(self.settings.cache_dir.rglob("*.mp3")))

    async def test_synthesis_timeout(self):
        self.provider.pause = 2
        client = await self.client(replace(self.settings, attempt_timeout=1, retries=0))
        response = await self.post(client)
        self.assertEqual(response.status, 504)
        self.assertEqual((await response.json())["error"]["code"], "timeout")

    async def test_packed_passage_recovers_from_provider_timeouts(self):
        passage = "Первое предложение. Второе предложение."
        left, right = split_for_retry(passage)
        calls = []

        async def synthesize(phrase, *, recover_no_audio=False):
            calls.append(phrase.text)
            if phrase.text == passage:
                raise TimeoutError
            await asyncio.sleep(0.6)
            return FRAME * (1 if phrase.text == left else 2)

        self.provider.synthesize = synthesize
        client = await self.client(replace(self.settings, request_timeout=1, passage_timeout=5, retry_backoff_ms=0))
        result = await self.post(client, text=passage, language="ru")
        self.assertEqual(result.status, 200)
        self.assertEqual(await result.read(), FRAME * 3)
        self.assertEqual(calls, [passage, passage, left, right])

    async def test_api_rate_limit(self):
        client = await self.client(replace(self.settings, requests_per_minute=1))
        with patch("backend.http_tts.clock", return_value=65):
            self.assertEqual((await self.post(client)).status, 200)
            limited = await self.post(client)
        self.assertEqual(limited.status, 429)
        self.assertEqual(limited.headers["Retry-After"], "55")
        self.assertEqual((await limited.json())["error"]["code"], "rate_limited")

    def test_rate_limiter_counts_a_peer_and_resets(self):
        from backend.http_tts import RateLimiter

        limiter = RateLimiter(1)
        with patch("backend.http_tts.clock", return_value=65) as tick:
            self.assertIsNone(limiter.retry_after("peer"))
            self.assertEqual(limiter.retry_after("peer"), 55)
            self.assertIsNone(limiter.retry_after("another peer"))
            tick.return_value = 121
            self.assertIsNone(limiter.retry_after("peer"))
