from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
#from .models import Item

class BaseController:
    """Parent controller providing shared utilities and hooks."""

    @classmethod
    def as_view(cls, action_name):
        """
        Dynamically routes the HTTP request to a specific controller action method,
        while acting as a central gateway for authentication or logging.
        """
        def view_wrapper(request, *args, **kwargs):
            # Shared Logic: Enforce authentication globally across all actions
            if not request.user.is_authenticated:
                return redirect('login') # Redirect unauthorized users

            # Instantiate the controller and fetch the requested method
            controller_instance = cls()
            action = getattr(controller_instance, action_name, None)

            if action is None:
                raise AttributeError(f"Action '{action_name}' not found on {cls.__name__}")

            return action(request, *args, **kwargs)
        return view_wrapper
