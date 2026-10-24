import time

from django.contrib.auth import logout
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


class AdminSecurityMiddleware:
    TIMEOUT = 300  # 5 minutos
    ADMIN_PATH = "/admin/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        is_admin = request.path.startswith(self.ADMIN_PATH)

        if user.is_authenticated:
            # Superusuarios: acceso exclusivo al Admin
            if user.is_superuser:
                if not is_admin:
                    return HttpResponseForbidden(
                        "Esta cuenta es exclusiva del administrador."
                    )

                now = time.time()
                last_activity = request.session.get("admin_last_activity")

                if last_activity is not None and now - last_activity >= self.TIMEOUT:
                    logout(request)
                    return redirect("/admin/login/")

                request.session["admin_last_activity"] = now

            # Usuarios comunes: prohibido acceder al Admin
            elif is_admin:
                return HttpResponseForbidden("Acceso exclusivo para superusuarios.")

        return self.get_response(request)
