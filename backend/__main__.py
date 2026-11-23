import os

from aiohttp import web

from .app import create_app
from .logs import configure_backend_logging
from .tts import env_int


if __name__ == "__main__":
    configure_backend_logging()
    web.run_app(
        create_app(),
        host=os.environ.get("ALAS_TTS_HOST", "127.0.0.1"),
        port=env_int("ALAS_TTS_PORT", 8000, 1, 65535),
    )
