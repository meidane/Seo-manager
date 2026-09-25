"""پردازنده‌های زمینه (context processors) سراسری."""


def notifications(request):
    """زنگولهٔ اعلان‌ها + بَجِ «بازبینی» برای هدر/سایدبار (بارِ اولِ صفحه، بدونِ AJAX).
    سبک: فقط شمارش + ۸ اعلانِ اخیر. بَجِ بازبینی = تعدادِ تسکِ بازبینی‌نشدهٔ قابل‌بازبینیِ کاربر."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    from .models import Notification
    qs = Notification.objects.filter(user=user)
    ctx = {
        'notif_unread': qs.filter(read=False).count(),
        'notif_recent': list(qs[:8]),
    }
    # بَجِ بازبینی (منبعِ واحد: tasks.queries.review_pending_count — پولینگِ زنده هم از
    # همان می‌خواند). فقط اگر کاربر اصلاً مسیرِ بازبینی دارد کوئری می‌زند.
    try:
        from tasks.queries import review_pending_count
        n = review_pending_count(request)
        if n:
            ctx['review_pending_count'] = n
    except Exception:  # noqa: BLE001
        pass
    return ctx
