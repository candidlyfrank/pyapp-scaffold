from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import path


def home(request):
    return render(request, "home.html")


def health(_request):
    return JsonResponse({"service": "django", "status": "ok", "port": 8090})


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
]
