from django.shortcuts import render
from django.http import HttpResponse

def say_hello(request: HttpResponse) -> HttpResponse:
    return HttpResponse("Hello, world!")