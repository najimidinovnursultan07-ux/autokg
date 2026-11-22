from django.contrib import messages
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import login as auth_login
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


SESSION_CHALLENGE = "admin_2fa_challenge"
SESSION_VERIFIED = "admin_2fa_verified"
LOGIN_FAILS_LIMIT = 10  # неудачных попыток пароля с одного IP
LOGIN_FAILS_WINDOW = 15 * 60


class AutoBuyAdminSite(AdminSite):
    site_header = "AutoBuy"
    site_title = "AutoBuy — администрирование"
    index_title = "Управление маркетплейсом"

    def has_permission(self, request):
        from apps.accounts.two_factor import requires_two_factor

        user = request.user
        if not (user.is_active and user.is_staff and getattr(user, "role", None) == "admin"):
            return False
        # Сессия без пройденного кода из Telegram в админку не пускает
        return not requires_two_factor(user) or request.session.get(SESSION_VERIFIED) is True

    def login(self, request, extra_context=None):
        from apps.accounts.two_factor import TwoFactorError, requires_two_factor, start_challenge, verify_challenge

        ip = request.META.get("REMOTE_ADDR", "")
        fails_key = f"admin-login-fails:{ip}"
        next_url = request.POST.get("next") or request.GET.get("next") or ""
        if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            next_url = ""
        context = {**self.each_context(request), "title": "Вход", "next": next_url, **(extra_context or {})}

        if request.method == "POST" and "code" in request.POST and request.session.get(SESSION_CHALLENGE):
            try:
                user = verify_challenge(request.session[SESSION_CHALLENGE], request.POST.get("code"))
            except TwoFactorError as exc:
                messages.error(request, str(exc))
                if exc.restart:
                    request.session.pop(SESSION_CHALLENGE, None)
                    return HttpResponseRedirect(request.get_full_path())
                return TemplateResponse(request, "admin/two_factor_code.html", context)
            auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            request.session[SESSION_VERIFIED] = True
            return HttpResponseRedirect(next_url or reverse("admin:index", current_app=self.name))

        if request.method == "POST":
            if (cache.get(fails_key) or 0) >= LOGIN_FAILS_LIMIT:
                messages.error(request, "Слишком много попыток входа. Подождите 15 минут.")
                return HttpResponseRedirect(request.get_full_path())
            form = AdminAuthenticationForm(request, data=request.POST)
            if not form.is_valid():
                cache.set(fails_key, (cache.get(fails_key) or 0) + 1, LOGIN_FAILS_WINDOW)
            else:
                user = form.get_user()
                if requires_two_factor(user):
                    try:
                        challenge = start_challenge(user, ip=ip)
                    except TwoFactorError as exc:
                        messages.error(request, str(exc))
                        return HttpResponseRedirect(request.get_full_path())
                    request.session[SESSION_CHALLENGE] = str(challenge.id)
                    return TemplateResponse(request, "admin/two_factor_code.html", context)

        request.session.pop(SESSION_CHALLENGE, None)
        return super().login(request, extra_context)
