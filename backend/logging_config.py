"""Logging policy.

Hard rule (security requirement): request bodies and monetary values are
never logged. Concretely that means:

- No middleware or handler reads and logs the request/response body.
- Uvicorn's access log records only method, path and status — it is left at
  its default and must not be reconfigured to include bodies or full query
  strings.
- Application code logs identifiers and counts, never amounts or credentials.

``RedactingFilter`` is a backstop: if a log record ever mentions a credential
field, its message is dropped rather than written.
"""

import logging

_FORBIDDEN = ("password", "secret", "authorization", "bearer ", "access_token")


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage().lower()
        except Exception:
            return True
        if any(token in message for token in _FORBIDDEN):
            record.msg = "[redacted: log line referenced a credential field]"
            record.args = ()
        return True


def configure_logging() -> None:
    redactor = RedactingFilter()
    for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error", "backend"):
        logger = logging.getLogger(name)
        if not any(isinstance(f, RedactingFilter) for f in logger.filters):
            logger.addFilter(redactor)
        for handler in logger.handlers:
            if not any(isinstance(f, RedactingFilter) for f in handler.filters):
                handler.addFilter(redactor)
