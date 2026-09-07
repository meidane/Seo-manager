"""ردیفِ خودکارِ «تولید محتوا» روی فاکتورِ متصل به گزارش — با اسنپ‌شات.

وقتی فاکتوری به گزارشی وصل می‌شود (دراپ‌داونِ صفحهٔ گزارش یا «＋ فاکتور جدید»)، اگر
هزینهٔ تولید محتوای گزارش > ۰ باشد یک ردیفِ فاکتور اضافه می‌شود. چون ردیفِ فاکتور یک
رکوردِ واقعی است، بعداً با تغییرِ نرخِ پروژه/گزارش عوض نمی‌شود (اسنپ‌شات). ۰ = هیچ ردیفی.
"""
CONTENT_LINE_MARK = 'تولید محتوا (خودکار)'


def ensure_content_invoice_line(report):
    """یک‌بار برای هر گزارش، ردیفِ «تولید محتوا» را به فاکتورِ متصل اضافه می‌کند.

    برمی‌گرداند ردیفِ ساخته‌شده یا None (بدونِ فاکتور / هزینهٔ ۰ / از قبل اضافه‌شده).
    """
    from finance.models import InvoiceLine
    inv = report.invoice
    if not inv:
        return None
    cost = report.content_cost()
    if cost['total'] <= 0:
        return None
    desc = f'{CONTENT_LINE_MARK} — گزارش #{report.id}'
    if inv.lines.filter(description=desc).exists():
        return None
    return InvoiceLine.objects.create(
        invoice=inv, order=inv.lines.count(),
        description=desc, qty=1, unit_price=cost['total'], tax=0, discount=0)
