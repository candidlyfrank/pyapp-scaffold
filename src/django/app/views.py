from django.shortcuts import render
from django.http import HttpResponse

_globalVars = {
    'name': "John Smith"
}

def say_hello(request: HttpResponse) -> HttpResponse:
    return render(request, "hello.html", _globalVars)