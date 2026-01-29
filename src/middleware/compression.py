"""
Compression middleware for the Regal POS Backend
Implements gzip compression for API responses
"""
import gzip
import io
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
import logging

logger = logging.getLogger(__name__)


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to compress responses using gzip
    """

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,  # Only compress if content is larger than this
        compress_empty: bool = False,  # Whether to compress empty responses
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compress_empty = compress_empty

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check if client accepts gzip compression
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            # Client doesn't support gzip, proceed normally
            response = await call_next(request)
            return response

        # Proceed with the request
        response = await call_next(request)

        # Check if response should be compressed
        should_compress = self._should_compress(response)

        if should_compress:
            # Compress the response content
            compressed_content = self._compress_content(response.body)

            # Create new response with compressed content
            compressed_response = Response(
                content=compressed_content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

            # Update headers for compressed content
            compressed_response.headers["Content-Encoding"] = "gzip"
            compressed_response.headers["Content-Length"] = str(len(compressed_content))

            logger.debug(f"Compressed response from {len(response.body)} to {len(compressed_content)} bytes")
            return compressed_response

        return response

    def _should_compress(self, response: Response) -> bool:
        """
        Determine if a response should be compressed
        """
        # Don't compress if content is too small
        if len(response.body) < self.minimum_size:
            return False

        # Don't compress if content is already encoded
        if response.headers.get("Content-Encoding"):
            return False

        # Don't compress if content type is not compressible
        content_type = response.headers.get("content-type", "").lower()
        if not self._is_compressible_content_type(content_type):
            return False

        return True

    def _is_compressible_content_type(self, content_type: str) -> bool:
        """
        Check if content type is compressible
        """
        compressible_types = [
            "text/",
            "application/json",
            "application/javascript",
            "application/xml",
            "application/rss+xml",
            "image/svg+xml",
            "application/xhtml+xml",
        ]

        for compressible_type in compressible_types:
            if compressible_type in content_type:
                return True

        return False

    def _compress_content(self, content: bytes) -> bytes:
        """
        Compress content using gzip
        """
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz_file:
            gz_file.write(content)
        return buf.getvalue()


# Alternative approach: Decorator for individual endpoints
def compress_response(minimum_size: int = 500):
    """
    Decorator to enable compression for specific endpoints
    """
    def decorator(func):
        import asyncio
        from functools import wraps

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the original function
            result = await func(*args, **kwargs)

            # Note: Actual compression would need to be handled differently
            # since we can't modify response headers from within a route handler
            # This is just a placeholder for the concept

            return result

        return wrapper

    return decorator


# Utility function to compress data manually if needed
def compress_data(data: bytes) -> bytes:
    """
    Compress data using gzip
    """
    return gzip.compress(data)


def decompress_data(data: bytes) -> bytes:
    """
    Decompress data using gzip
    """
    return gzip.decompress(data)