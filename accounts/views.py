"""ویوهای احراز هویت — ورود و خروج."""
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy


class LoginView(auth_views.LoginView):
    """صفحه‌ی ورود با تمپلیت اختصاصی و ریدایرکت کاربرانِ واردشده."""

    template_name = 'registration/login.html'
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    """خروج و بازگشت به صفحه‌ی ورود."""

    next_page = reverse_lazy('accounts:login')
