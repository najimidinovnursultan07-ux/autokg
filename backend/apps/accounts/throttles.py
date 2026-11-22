from rest_framework.throttling import SimpleRateThrottle


class LoginAccountRateThrottle(SimpleRateThrottle):
    """
    Лимит попыток входа на один email — независимо от IP.

    Лимит по IP не спасает от подбора пароля с множества адресов (ботнет,
    прокси). Этот лимит считает попытки для конкретного аккаунта.
    """

    scope = "auth_account"

    def get_cache_key(self, request, view):
        email = request.data.get("email") if hasattr(request, "data") else None
        if not email or not isinstance(email, str):
            return None
        return self.cache_format % {"scope": self.scope, "ident": email.strip().lower()}
