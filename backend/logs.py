import logging
import re


class BackendLogFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        return re.sub(r"(?i)([?&](?:TrustedClientToken|Sec-MS-GEC)=)[^&\s'\"]+", r"\1[redacted]", message)


def configure_backend_logging() -> None:
    logger = logging.getLogger("backend")
    handler = logging.StreamHandler()
    handler.setFormatter(BackendLogFormatter("%(levelname)s:%(name)s:%(message)s"))
    logger.handlers[:] = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
