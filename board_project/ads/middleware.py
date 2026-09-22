from django.shortcuts import redirect
from django.urls import resolve


class BanMiddleware:
    """Перенаправляет забаненных на страницу /banned/, кроме logout и самой страницы."""

    EXEMPT_URLS = {'banned', 'logout', 'login'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile and profile.is_banned:
                url_name = resolve(request.path_info).url_name
                if url_name not in self.EXEMPT_URLS and not request.path.startswith('/admin/'):
                    return redirect('banned')
        return self.get_response(request)