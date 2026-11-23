import asyncio
import logging
from time import monotonic as clock

from aiohttp import web
from filelock import Timeout as LockTimeout

from .tts import (
    MAX_TEXT_CHARS, Busy, EdgeProvider, InvalidVoice, ProviderFailure, ProviderHttpError,
    ProviderNetworkError, ProviderNoAudio, Settings, SpeechProvider, SpeechService, parse_phrase,
)

LOGGER = logging.getLogger(__name__)


def error(status: int, code: str, message: str, retry_after: int | None = None) -> web.Response:
    headers = {"Cache-Control": "no-store"}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return web.json_response({"error": {"code": code, "message": message}}, status=status, headers=headers)


class RateLimiter:
    def __init__(self, limit: int):
        self.limit = limit
        self.window = -1
        self.counts: dict[str, int] = {}

    def retry_after(self, peer: str) -> int | None:
        now = int(clock())
        window, remainder = divmod(now, 60)
        if window != self.window:
            self.counts.clear()
            self.window = window
        count = self.counts.get(peer, 0)
        if count >= self.limit or (peer not in self.counts and len(self.counts) >= 4096):
            return 60 - remainder
        self.counts[peer] = count + 1
        return None


def create_app(settings: Settings | None = None, provider: SpeechProvider | None = None) -> web.Application:
    settings = settings or Settings.from_env()
    service = SpeechService(settings, provider or EdgeProvider())
    limiter = RateLimiter(settings.requests_per_minute)
    active = 0
    app = web.Application(client_max_size=MAX_TEXT_CHARS * 12 + 1024)

    async def lifecycle(_: web.Application):
        await asyncio.to_thread(service.cache.initialize)

        async def prune():
            while True:
                await asyncio.sleep(min(3600, settings.cache_seconds))
                try:
                    await asyncio.to_thread(service.cache.prune)
                except (OSError, LockTimeout):
                    LOGGER.warning("TTS cache maintenance failed", exc_info=True)

        maintenance = asyncio.create_task(prune())
        try:
            yield
        finally:
            maintenance.cancel()
            await asyncio.gather(maintenance, return_exceptions=True)
            await service.close()

    async def tts(request: web.Request) -> web.Response:
        nonlocal active
        delay = limiter.retry_after(request.remote or "unknown")
        if delay is not None:
            return error(429, "rate_limited", "Too many pronunciation requests. Try again shortly.", delay)
        if active >= settings.pending + settings.concurrency + 32:
            return error(503, "busy", "The pronunciation service is busy. Try again shortly.", 2)

        active += 1
        try:
            if request.content_type != "application/json":
                return error(415, "invalid_content_type", "Send the request as application/json.")
            try:
                async with asyncio.timeout(5):
                    payload = await request.json()
            except web.HTTPRequestEntityTooLarge:
                return error(413, "body_too_large", "The request body is too large.")
            except (ValueError, LookupError, RecursionError):
                return error(400, "invalid_json", "The request must contain valid JSON.")
            except TimeoutError:
                return error(408, "body_timeout", "The request body took too long to arrive.")
            try:
                phrase = parse_phrase(payload)
            except InvalidVoice as exc:
                return error(400, "invalid_voice", str(exc))
            except ValueError as exc:
                return error(400, "invalid_input", str(exc))
            LOGGER.info("TTS request input_chars=%d normalized_chars=%d", len(payload["text"]), len(phrase.text))

            try:
                audio, cached = await service.get(phrase)
                return web.Response(body=audio, content_type="audio/mpeg", headers={
                    "Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff",
                    "X-TTS-Cache": "HIT" if cached else "MISS",
                })
            except (Busy, LockTimeout):
                return error(503, "busy", "The pronunciation service is busy. Try again shortly.", 2)
            except TimeoutError:
                LOGGER.warning("TTS request timed out", exc_info=True)
                return error(504, "timeout", "Pronunciation took too long. Please try again.")
            except ProviderNoAudio:
                return error(503, "provider_no_audio", "The speech provider produced no audio. Please try again.", 2)
            except ProviderNetworkError:
                return error(502, "provider_network_error", "The connection to the speech provider failed.")
            except ProviderHttpError as exc:
                if exc.retryable:
                    return error(503, "provider_http_error", "The speech provider is temporarily unavailable.", 2)
                return error(502, "provider_http_error", "The speech provider rejected the synthesis request.")
            except ProviderFailure:
                return error(502, "synthesis_failed", "The speech provider did not produce complete audio.")
            except Exception as exc:
                LOGGER.exception("TTS internal error (%s)", type(exc).__name__)
                return error(500, "internal_error", "The pronunciation service encountered an internal error.")
        finally:
            active -= 1

    app.cleanup_ctx.append(lifecycle)
    app.router.add_post("/api/tts", tts)
    return app
