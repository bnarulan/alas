import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from aiohttp import web

from backend.app import create_app
from backend.tts import Phrase, Settings
from tests.audio_fixture import SILENT_MP3


class BrowserProvider:
    async def synthesize(self, _: Phrase, *, recover_no_audio: bool = False) -> bytes:
        await asyncio.sleep(0.18)
        return SILENT_MP3


if __name__ == "__main__":
    with TemporaryDirectory(prefix="alas-tts-browser-") as cache_dir:
        app = create_app(Settings(cache_dir=Path(cache_dir), requests_per_minute=600), BrowserProvider())
        web.run_app(app, host="127.0.0.1", port=4180, print=None)
