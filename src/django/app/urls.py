from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import path, include
from . import views


def home(request):
    return render(request, "home.html")


def health(_request):
    return JsonResponse({"service": "django", "status": "ok", "port": 8090})


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("playground/", home, name="home"),
    path("playground/hello/", views.say_hello, name="hello-world"),
]

# django debug toolbar
urlpatterns += [path("__debug__/", include("debug_toolbar.urls")),]
