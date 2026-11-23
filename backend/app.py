import asyncio
import logging

from aiohttp import web
from filelock import Timeout as LockTimeout

from .http_tts import MAX_BODY_BYTES, RequestTooLarge, TtsEndpoint
from .tts import EdgeProvider, Settings, SpeechProvider, SpeechService

LOGGER = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, provider: SpeechProvider | None = None) -> web.Application:
    settings = settings or Settings.from_env()
    service = SpeechService(settings, provider or EdgeProvider())
    endpoint = TtsEndpoint(service)
    app = web.Application(client_max_size=MAX_BODY_BYTES)

    async def lifecycle(_: web.Application):
        cache = service.cache
        assert cache is not None
        await asyncio.to_thread(cache.initialize)

        async def prune():
            while True:
                await asyncio.sleep(min(3600, settings.cache_seconds))
                try:
                    await asyncio.to_thread(cache.prune)
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
        async def load_json():
            try:
                return await request.json()
            except web.HTTPRequestEntityTooLarge as exc:
                raise RequestTooLarge from exc

        result = await endpoint.respond(request.remote or "unknown", request.content_type, load_json)
        if isinstance(result.body, bytes):
            return web.Response(body=result.body, status=result.status, content_type="audio/mpeg", headers=result.headers)
        return web.json_response(result.body, status=result.status, headers=result.headers)

    app.cleanup_ctx.append(lifecycle)
    app.router.add_post("/api/tts", tts)
    return app
