# File: api/middleware.py
from django.http import HttpResponse

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