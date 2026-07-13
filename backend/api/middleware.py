import logging
import time

from django.http import HttpResponse

request_logger = logging.getLogger("api.requests")


class RequestLoggingMiddleware:
    """
    Lightweight request/response logging for development diagnostics.

    This keeps frontend-triggered API activity visible in the backend terminal,
    including multipart uploads.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.perf_counter()
        method = getattr(request, "method", "UNKNOWN")
        path = getattr(request, "path", "")
        content_type = request.META.get("CONTENT_TYPE", "")
        file_names = [uploaded_file.name for uploaded_file in request.FILES.values()]

        request_logger.info(
            "REQUEST START method=%s path=%s query=%s content_type=%s files=%s",
            method,
            path,
            request.META.get("QUERY_STRING", ""),
            content_type,
            file_names,
        )

        try:
            response = self.get_response(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            request_logger.exception(
                "REQUEST ERROR method=%s path=%s duration_ms=%s",
                method,
                path,
                elapsed_ms,
            )
            raise

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        request_logger.info(
            "REQUEST END method=%s path=%s status=%s duration_ms=%s",
            method,
            path,
            getattr(response, "status_code", "UNKNOWN"),
            elapsed_ms,
        )
        return response

class IgnoreWellKnownMiddleware:
    """
    Middleware to handle requests to /.well-known/ paths.
    Returns a 204 No Content response for such requests.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Handle only `.well-known` requests
        if request.path.startswith('/.well-known/'):
            # Allow specific `.well-known` routes to pass through
            allowed_routes = [
                '/.well-known/valid-route/',  # Example of a valid route
            ]
            if request.path not in allowed_routes:
                return HttpResponse(status=204)  # No Content
        return self.get_response(request)
