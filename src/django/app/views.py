from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

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
