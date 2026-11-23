import json
import logging
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from api.tts import create_app
from backend.http_tts import MAX_BODY_BYTES
from backend.logs import BackendLogFormatter
from backend.mp3 import inspect_mp3
from backend.speech_text import split_passage
from backend.tts import ProviderNetworkError, Settings
from tests.test_tts import FakeProvider


async def post(app, body: bytes, *, content_type: bytes = b"application/json", method: str = "POST"):
    chunks = iter((body[:20], body[20:]))
    events = []

    async def receive():
        chunk = next(chunks, None)
        if chunk is None:
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.request", "body": chunk, "more_body": True}

    async def send(event):
        events.append(event)

    await app({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "path": "/api/tts", "root_path": "", "query_string": b"",
        "scheme": "https", "headers": [(b"content-type", content_type)],
        "client": ("127.0.0.1", 51000), "server": ("local", 443),
    }, receive, send)
    return events[0]["status"], dict(events[0]["headers"]), events[1]["body"]


def payload(text="Білім", language="kk", **options):
    return json.dumps(dict(text=text, language=language, **options), ensure_ascii=False).encode("utf-8")


class VercelTtsTests(unittest.IsolatedAsyncioTestCase):
    async def test_voices_and_no_disk_cache(self):
        with TemporaryDirectory() as directory:
            cache_dir = Path(directory) / "must-not-be-created"
            provider = FakeProvider()
            app = create_app(Settings(cache_dir=cache_dir), provider)
            for body in (payload(), payload(), payload("Сәлем", voice="male"), payload("Образование", "ru"), payload("Текст", "ru", voice="male", speed=0.9)):
                status, headers, audio = await post(app, body)
                self.assertEqual(status, 200)
                self.assertEqual(headers[b"content-type"], b"audio/mpeg")
                self.assertEqual(headers[b"x-tts-cache"], b"DISABLED")
                self.assertEqual(headers[b"x-alas-playback-cache"], b"session-v1")
                self.assertIsNotNone(inspect_mp3(audio))
            self.assertEqual([call.voice for call in provider.calls], [
                "kk-KZ-AigulNeural", "kk-KZ-AigulNeural", "kk-KZ-DauletNeural", "ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural",
            ])
            self.assertEqual(provider.calls[-1].rate, "-10%")
            self.assertFalse(cache_dir.exists())

    async def test_full_kazakh_lesson_includes_last_chunk(self):
        seed = (Path(__file__).resolve().parents[1] / "src/data/seed.ts").read_text(encoding="utf-8")
        lesson = re.search(r"text: '(Ресми-іскерлік стиль әкімшілік[^']+)'", seed)[1].replace(r"\n", "\n")
        expected = split_passage(lesson)
        self.assertGreater(len(expected), 1)
        provider = FakeProvider()
        app = create_app(Settings(cache_dir=Path("unused")), provider)
        status, _, audio = await post(app, payload(lesson))
        self.assertEqual(status, 200)
        self.assertEqual([call.text for call in provider.calls], expected)
        self.assertTrue(provider.calls[-1].text.endswith("осы стильде жазылады."))
        self.assertEqual(inspect_mp3(audio).frames, len(expected) * inspect_mp3(provider.audio).frames)

    async def test_invalid_provider_audio_network_and_response_limit(self):
        provider = FakeProvider()
        app = create_app(Settings(cache_dir=Path("unused"), retries=0, max_audio_bytes=50), provider)
        for failure, status_code, code in (
            (ProviderNetworkError("private network details"), 502, "provider_network_error"),
            (TimeoutError("private timeout details"), 504, "timeout"),
            (None, 413, "audio_too_large"),
        ):
            if failure:
                provider.failures.append(failure)
            status, headers, body = await post(app, payload())
            self.assertEqual(status, status_code)
            self.assertEqual(headers[b"content-type"], b"application/json")
            self.assertNotIn(b"x-alas-playback-cache", headers)
            self.assertEqual(json.loads(body)["error"]["code"], code)
            self.assertNotIn(b"private", body)
        provider.audio = b"partial MP3"
        status, _, body = await post(app, payload())
        self.assertEqual(status, 502)
        self.assertEqual(json.loads(body)["error"]["code"], "synthesis_failed")

    async def test_request_validation(self):
        provider = FakeProvider()
        app = create_app(Settings(cache_dir=Path("unused")), provider)
        for body, status_code, code in (
            (b"{", 400, "invalid_json"),
            (payload(voice="unapproved"), 400, "invalid_voice"),
            (payload(""), 400, "invalid_input"),
            (b"x" * (MAX_BODY_BYTES + 1), 413, "body_too_large"),
        ):
            status, _, body = await post(app, body)
            self.assertEqual(status, status_code)
            self.assertEqual(json.loads(body)["error"]["code"], code)
        self.assertEqual((await post(app, b"", content_type=b"text/plain"))[0], 415)
        self.assertEqual((await post(app, b"", method="GET"))[0], 405)
        self.assertEqual(provider.calls, [])


class VercelLoggingTests(unittest.TestCase):
    def test_provider_query_values_are_redacted(self):
        try:
            raise RuntimeError("wss://provider/?TrustedClientToken=secret&Sec-MS-GEC=signature")
        except RuntimeError as exc:
            formatter = BackendLogFormatter()
            record = logging.LogRecord("backend", logging.WARNING, __file__, 1, "Provider failed", (), (type(exc), exc, exc.__traceback__))
            self.assertIn("TrustedClientToken=[redacted]&Sec-MS-GEC=[redacted]", formatter.format(record))
