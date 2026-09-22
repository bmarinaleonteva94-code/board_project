from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect


def not_banned(view_func):
    """Запрещает доступ забаненным пользователям."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile and profile.is_banned:
                messages.error(request, f'Вы забанены. Причина: {profile.ban_reason or "—"}')
                return redirect('banned')
        return view_func(request, *args, **kwargs)
    return wrapper