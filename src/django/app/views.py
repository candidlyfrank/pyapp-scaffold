import asyncio
import json
import random
from json import JSONDecodeError
from uuid import uuid4

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.csrf import csrf_failure as default_csrf_failure
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

MAX_CHAT_MESSAGE_LENGTH = 500
# A dedicated generator keeps the mock latency isolated and avoids security-linter warnings.
_delay_random = random.SystemRandom()

_globalVars = {
    'name': "John Smith"
}

def say_hello(request: HttpResponse) -> HttpResponse:
    return render(request, "hello.html", _globalVars)


@ensure_csrf_cookie
def session_api(request):
    user = request.user
    return JsonResponse(
        {
            "authenticated": user.is_authenticated,
            "username": user.username if user.is_authenticated else None,
        }
    )


@require_POST
def example_mutation(_request):
    return JsonResponse({"status": "saved"})


def chat_error(code: str, message: str, *, status: int) -> JsonResponse:
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def csrf_failure(request, reason=""):
    if request.path.startswith("/api/"):
        return JsonResponse(
            {
                "error": {
                    "code": "csrf_failed",
                    "message": "CSRF verification failed. Refresh the page and try again.",
                }
            },
            status=403,
        )

    return default_csrf_failure(request, reason=reason)


@require_POST
async def chat_api(request):
    if request.content_type != "application/json":
        return chat_error(
            "unsupported_media_type",
            "Content-Type must be application/json.",
            status=415,
        )

    try:
        payload = json.loads(request.body)
    except (JSONDecodeError, UnicodeDecodeError):
        return chat_error("malformed_json", "Request body must be valid JSON.", status=400)

    content = payload.get("content") if isinstance(payload, dict) else None
    if not isinstance(content, str):
        return chat_error(
            "invalid_content",
            "Message must contain between 1 and 500 characters.",
            status=400,
        )

    content = content.strip()
    if not content or len(content) > MAX_CHAT_MESSAGE_LENGTH:
        return chat_error(
            "invalid_content",
            "Message must contain between 1 and 500 characters.",
            status=400,
        )

    # Keep the mock realistic without occupying a Django worker thread while it waits.
    await asyncio.sleep(_delay_random.uniform(1.0, 2.0))
    return JsonResponse(
        {
            "id": str(uuid4()),
            "content": f"Thanks for your message: {content}",
            "sender": "assistant",
            "timestamp": timezone.now().isoformat(),
        }
    )
