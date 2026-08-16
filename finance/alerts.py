"""هشدارهای حسابداری — تشخیصِ ناسازگاری‌های محتمل (نرم، بدونِ بلاک‌کردن).

هر هشدار: {level: 'danger'|'warn', icon, title, detail, url}. روی داشبورد نمایش داده می‌شوند
و در تبِ گزارش هم به‌صورتِ بنرِ متنی برای موردِ در حالِ مشاهده.
"""
from django.urls import reverse

from projects.models import Project

from .balances import project_balances, salary_balances
from .models import BankAccount, Category


def _money(n):
    try:
        from core import jalali as j
        return j.to_fa_digits(f'{int(round(float(n))):,}')
    except Exception:  # noqa: BLE001
        return str(n)


def compute_alerts():
    """فهرستِ هشدارها برای سازمانِ جاری (مدل‌ها به‌صورتِ خودکار به سازمان اسکوپ‌اند)."""
    out = []

    # ۱) مانده‌ی بانکِ منفی
    for b in BankAccount.objects.filter(is_active=True):
        if b.balance < 0:
            out.append({
                'level': 'danger', 'icon': '🏦',
                'title': f'مانده‌ی «{b.name}» منفی است',
                'detail': f'مانده: {_money(b.balance)} — احتمالاً تراکنشی جا افتاده',
                'url': reverse('finance:banks'),
            })

    # ۲) مانده‌ی پروژه‌ی مثبت (واریزی بیش از فاکتورها → شاید فاکتوری ثبت نشده)
    pnames = dict(Project.objects.values_list('id', 'name'))
    for pid, bal in project_balances(list(pnames)).items():
        if bal > 0:
            out.append({
                'level': 'warn', 'icon': '🧾',
                'title': f'مانده‌ی پروژه‌ی «{pnames.get(pid, "")}» مثبت است',
                'detail': f'واریزی {_money(bal)} بیشتر از فاکتورهاست — شاید فاکتوری ثبت نشده',
                'url': reverse('finance:ledger') + f'?project={pid}',
            })

    # ۳) اضافه‌پرداختِ حقوق (برداشتِ حقوق بیش از تعهد)
    sal_cats = list(Category.objects.filter(colleague__isnull=False).select_related('colleague'))
    sb = salary_balances([c.colleague_id for c in sal_cats])
    for c in sal_cats:
        bal = sb.get(c.colleague_id, 0)
        if bal < 0:
            out.append({
                'level': 'warn', 'icon': '💰',
                'title': f'حقوقِ «{c.colleague.full_name}» بیش از تعهد پرداخت شده',
                'detail': f'اضافه‌پرداخت: {_money(-bal)}',
                'url': reverse('finance:ledger') + f'?category={c.id}',
            })

    return out
