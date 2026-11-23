import json
import os
from dataclasses import replace

from starlette.applications import Starlette
from starlette.requests import ClientDisconnect, Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from backend.http_tts import MAX_BODY_BYTES, RequestTooLarge, TtsEndpoint
from backend.logs import configure_backend_logging
from backend.tts import EdgeProvider, Settings, SpeechProvider, SpeechService

# Headroom for cold start, request parsing and Vercel's response envelope.
PASSAGE_TIMEOUT = 240
MAX_RESPONSE_BYTES = 4_000_000


def create_app(settings: Settings | None = None, provider: SpeechProvider | None = None) -> Starlette:
    settings = settings or Settings.from_env()
    settings = replace(
        settings,
        passage_timeout=min(settings.passage_timeout, PASSAGE_TIMEOUT),
        max_audio_bytes=min(settings.max_audio_bytes, MAX_RESPONSE_BYTES),
    )
    endpoint = TtsEndpoint(SpeechService(settings, provider or EdgeProvider(), disk_cache=False))

    async def tts(request: Request) -> Response:
        async def load_json():
            body = bytearray()
            try:
                async for chunk in request.stream():
                    if len(body) + len(chunk) > MAX_BODY_BYTES:
                        raise RequestTooLarge
                    body.extend(chunk)
            except ClientDisconnect as exc:
                raise ValueError("Incomplete request body") from exc
            return json.loads(body.decode("utf-8"))

        content_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
        peer = request.client.host if request.client else "unknown"
        if os.environ.get("VERCEL") == "1":
            peer = request.headers.get("x-vercel-forwarded-for", peer)
        result = await endpoint.respond(peer, content_type, load_json)
        if isinstance(result.body, bytes):
            return Response(result.body, status_code=result.status, media_type="audio/mpeg", headers={
                **result.headers,
                "X-TTS-Cache": "DISABLED",
                "X-Alas-Playback-Cache": "session-v1",
            })
        return JSONResponse(result.body, status_code=result.status, headers=result.headers)

    return Starlette(routes=[Route("/api/tts", tts, methods=["POST"])])


if os.environ.get("VERCEL") == "1":
    configure_backend_logging()

app = create_app()
