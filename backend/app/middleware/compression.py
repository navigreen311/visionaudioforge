"""GZip response compression middleware."""

from starlette.middleware.gzip import GZipMiddleware

# Re-export so main.py can do:
#   from app.middleware.compression import GZipMiddleware, GZIP_MINIMUM_SIZE
GZIP_MINIMUM_SIZE = 1000

__all__ = ["GZipMiddleware", "GZIP_MINIMUM_SIZE"]
