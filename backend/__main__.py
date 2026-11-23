import logging
import os
import re

from aiohttp import web

from .app import create_app
from .tts import env_int


class BackendLogFormatter(logging.Formatter):
    def formatException(self, exc_info):
        traceback = super().formatException(exc_info)
        return re.sub(r"(?i)([?&](?:TrustedClientToken|Sec-MS-GEC)=)[^&\s'\"]+", r"\1[redacted]", traceback)


if __name__ == "__main__":
    handler = logging.StreamHandler()
    handler.setFormatter(BackendLogFormatter("%(levelname)s:%(name)s:%(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    web.run_app(
        create_app(),
        host=os.environ.get("ALAS_TTS_HOST", "127.0.0.1"),
        port=env_int("ALAS_TTS_PORT", 8000, 1, 65535),
    )
