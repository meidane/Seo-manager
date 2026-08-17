"""محاسبه‌ی مانده‌ی «گردش حساب» — منبعِ واحد برای ستونِ مانده‌ی فاکتور/حقوق، هشدارها و بنرِ گزارش.

قرارداد علامت (مثلِ صورت‌حسابِ بانکی): مانده = Σواریز − Σبرداشت.
- پروژه: واریز = واریزِ تراکنش‌های پروژه؛ برداشت = جمعِ فاکتورها + برداشتِ تراکنش‌های پروژه.
  مانده‌ی منفی = هنوز طلبکاریم (فاکتور بیش از دریافتی)؛ مثبت = دریافتی بیش از فاکتورها.
- حقوقِ همکار: واریز = تعهدِ حقوق‌ها؛ برداشت = پرداختیِ تراکنش‌های بابتِ حقوقِ او.
  مانده‌ی مثبت = هنوز بدهکارِ همکاریم؛ منفی = اضافه‌پرداخت.
"""
from django.db.models import DecimalField, ExpressionWrapper, F, Sum

from .models import InvoiceLine, PayrollItem, Transaction

_LINE_TOTAL = ExpressionWrapper(
    F('qty') * F('unit_price') + F('tax') - F('discount'),
    output_field=DecimalField(max_digits=20, decimal_places=2))


def _int_ids(ids):
    """id‌ها را به int نرمال می‌کند (ورودی ممکن است رشته‌ی GET باشد؛ کلیدهای annotate int‌اند)."""
    out = []
    for i in ids:
        try:
            out.append(int(i))
        except (TypeError, ValueError):
            continue
    return out


def project_balances(project_ids):
    """{project_id: مانده} برای پروژه‌های داده‌شده (کلِ تاریخ، بدون بازه)."""
    ids = _int_ids(project_ids)
    if not ids:
        return {}
    tx = {r['project_id']: r for r in Transaction.objects
          .filter(project_id__in=ids).values('project_id')
          .annotate(d=Sum('deposit'), w=Sum('withdrawal'))}
    inv = {r['invoice__project_id']: r['s'] for r in InvoiceLine.objects
           .filter(invoice__project_id__in=ids).values('invoice__project_id')
           .annotate(s=Sum(_LINE_TOTAL))}
    out = {}
    for pid in ids:
        t = tx.get(pid) or {}
        out[pid] = int(t.get('d') or 0) - int(t.get('w') or 0) - int(inv.get(pid) or 0)
    return out


def project_balance(project_id):
    return project_balances([project_id]).get(int(project_id), 0)


def salary_balances(colleague_ids):
    """{colleague_id: مانده} = Σتعهدِ حقوق − Σبرداشتِ تراکنش‌های بابتِ حقوقِ او."""
    ids = _int_ids(colleague_ids)
    if not ids:
        return {}
    owed = {r['payroll__colleague_id']: r['s'] or 0 for r in PayrollItem.objects
            .filter(payroll__colleague_id__in=ids).values('payroll__colleague_id')
            .annotate(s=Sum('amount'))}
    paid = {r['categories__colleague_id']: r['s'] or 0 for r in Transaction.objects
            .filter(categories__colleague_id__in=ids).values('categories__colleague_id')
            .annotate(s=Sum('withdrawal'))}
    return {cid: int(owed.get(cid, 0)) - int(paid.get(cid, 0)) for cid in ids}


def salary_balance(colleague_id):
    return salary_balances([colleague_id]).get(int(colleague_id), 0)
