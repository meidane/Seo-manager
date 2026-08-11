"""کوئری‌های مشترکِ تسک — منبعِ واحد برای هر جایی که همین منطق لازم است
(صفحه‌ی بازبینی + فیدِ بازبینیِ داشبورد)، تا دو جا به‌صورتِ موازی درست/نادرست نشوند."""
from django.db.models import Q


def reviewable_q(request):
    """این تسک برای کاربرِ جاری قابل‌بازبینی است؟ دو مسیرِ مستقلِ OR‌شده:
    (۱) `assignee.needs_review=True` و مدیرِ همان همکار خودِ کاربر است (مستقل از
    دسترسیِ سازمانیِ `review`)؛ (۲) `type_def.requires_review=True`، فقط اگر کاربر
    دسترسیِ سازمانیِ `review` را داشته باشد."""
    m = getattr(request, 'membership', None)
    q = Q(assignee__needs_review=True, assignee__manager__user=request.user)
    if m and m.can('review'):
        q |= Q(type_def__requires_review=True)
    return q
