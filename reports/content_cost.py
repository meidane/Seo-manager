"""ردیفِ خودکارِ «تولید محتوا» روی فاکتورِ متصل به گزارش.

با هر ذخیرهٔ گزارش (و موقعِ اتصالِ فاکتور)، مبلغِ هزینهٔ تولید محتوا روی فاکتور **همگام**
می‌شود: اگر > ۰ باشد ردیف ساخته/به‌روزرسانی می‌شود، اگر ۰ شد حذف می‌شود. یک ردیفِ نشان‌دار
به‌ازای هر گزارش (با `description` مشخص).
"""
CONTENT_LINE_MARK = 'تولید محتوا (خودکار)'


def _line_desc(report):
    return f'{CONTENT_LINE_MARK} — گزارش #{report.id}'


def sync_content_invoice_line(report):
    """ردیفِ «تولید محتوا» را روی فاکتورِ متصل با هزینهٔ فعلی همگام می‌کند.

    - بدونِ فاکتور → کاری نمی‌کند.
    - هزینه > ۰ → ردیف را می‌سازد یا مبلغش را آپدیت می‌کند.
    - هزینه = ۰ → اگر ردیفِ خودکاری بود حذفش می‌کند.
    برمی‌گرداند مبلغِ نهاییِ ردیف (۰ یعنی بدونِ ردیف).
    """
    from finance.models import InvoiceLine
    inv = report.invoice
    if not inv:
        return 0
    total = report.content_cost()['total']
    desc = _line_desc(report)
    existing = inv.lines.filter(description=desc).first()
    if total <= 0:
        if existing:
            existing.delete()
        return 0
    if existing:
        if int(existing.unit_price) != int(total) or int(existing.qty) != 1:
            existing.unit_price = total
            existing.qty = 1
            existing.tax = 0
            existing.discount = 0
            existing.save(update_fields=['unit_price', 'qty', 'tax', 'discount'])
    else:
        InvoiceLine.objects.create(
            invoice=inv, order=inv.lines.count(),
            description=desc, qty=1, unit_price=total, tax=0, discount=0)
    return total


# سازگاری با کدِ قبلی (اتصالِ فاکتور) — همان sync
def ensure_content_invoice_line(report):
    return sync_content_invoice_line(report)
