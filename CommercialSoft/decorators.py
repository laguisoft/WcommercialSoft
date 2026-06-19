from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def client_required(view_func):
    """Reserve la vue aux comptes du portail client (lies a une fiche Client)."""
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'client_profile'):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
