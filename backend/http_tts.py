import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic as clock

from filelock import Timeout as LockTimeout

from .tts import (
    MAX_TEXT_CHARS, AudioTooLarge, Busy, InvalidVoice, ProviderFailure, ProviderHttpError,
    ProviderNetworkError, ProviderNoAudio, SpeechService, parse_phrase,
)

LOGGER = logging.getLogger(__name__)
MAX_BODY_BYTES = MAX_TEXT_CHARS * 12 + 1024


class RequestTooLarge(Exception):
    pass


@dataclass(frozen=True)
class TtsResponse:
    status: int
    body: bytes | dict
    headers: dict[str, str]


def error(status: int, code: str, message: str, retry_after: int | None = None) -> TtsResponse:
    headers = {"Cache-Control": "no-store"}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return TtsResponse(status, {"error": {"code": code, "message": message}}, headers)


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


class TtsEndpoint:
    def __init__(self, service: SpeechService):
        self.service = service
        self.limiter = RateLimiter(service.settings.requests_per_minute)
        self.active = 0

    async def respond(self, peer: str, content_type: str, load_json: Callable[[], Awaitable[object]]) -> TtsResponse:
        delay = self.limiter.retry_after(peer)
        if delay is not None:
            return error(429, "rate_limited", "Too many pronunciation requests. Try again shortly.", delay)
        settings = self.service.settings
        if self.active >= settings.pending + settings.concurrency + 32:
            return error(503, "busy", "The pronunciation service is busy. Try again shortly.", 2)

        self.active += 1
        try:
            if content_type != "application/json":
                return error(415, "invalid_content_type", "Send the request as application/json.")
            try:
                async with asyncio.timeout(5):
                    payload = await load_json()
            except RequestTooLarge:
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
                audio, cached = await self.service.get(phrase)
                return TtsResponse(200, audio, {
                    "Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff",
                    "X-TTS-Cache": "HIT" if cached else "MISS",
                })
            except (Busy, LockTimeout):
                return error(503, "busy", "The pronunciation service is busy. Try again shortly.", 2)
            except TimeoutError:
                LOGGER.warning("TTS request timed out", exc_info=True)
                return error(504, "timeout", "Pronunciation took too long. Please try again.")
            except AudioTooLarge:
                return error(413, "audio_too_large", "The audio exceeds the response size limit. Try a shorter passage.")
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
            self.active -= 1
