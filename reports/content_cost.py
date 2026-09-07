"""ردیفِ خودکارِ «تولید محتوا» روی فاکتورِ متصل به گزارش.

با هر ذخیرهٔ گزارش (و موقعِ اتصالِ فاکتور)، مبلغِ هزینهٔ تولید محتوا روی فاکتور **همگام**
می‌شود: اگر > ۰ باشد ردیف ساخته/به‌روزرسانی می‌شود، اگر ۰ شد حذف می‌شود. یک ردیف به‌ازای
هر گزارش، با بابتِ «تولید محتوا» و شرحِ «تولید محتوا - گزارش <ماه> <سال>».
"""
_LEGACY_PREFIX = 'تولید محتوا (خودکار)'   # فرمتِ قدیمی — موقعِ sync پاک/جایگزین می‌شود
CONTENT_CATEGORY_NAME = 'تولید محتوا'


def _line_desc(report):
    """«تولید محتوا - گزارش <ماهِ شمسی> <سال>» از بازهٔ گزارش (بدونِ عنوان/#id)."""
    from core.jalali import MONTH_NAMES, g2j
    label = ''
    if report.date_from:
        jd = g2j(report.date_from)
        label = f' - گزارش {MONTH_NAMES[jd.month - 1]} {jd.year}'
    return f'{CONTENT_CATEGORY_NAME}{label}'


def _content_category(report):
    """بابتِ «تولید محتوا» را در سازمانِ گزارش می‌سازد/برمی‌گرداند (درآمد از فاکتور)."""
    from finance.models import Category
    cat, _ = Category.all_objects.get_or_create(
        organization_id=report.organization_id, name=CONTENT_CATEGORY_NAME,
        defaults={'color': '#A78BFA', 'income_source': Category.INCOME_INVOICE})
    return cat


def sync_content_invoice_line(report):
    """ردیفِ «تولید محتوا» را روی فاکتورِ متصل با هزینهٔ فعلی همگام می‌کند.

    - بدونِ فاکتور → کاری نمی‌کند.
    - هزینه > ۰ → ردیف را می‌سازد یا مبلغ/بابت/شرحش را آپدیت می‌کند.
    - هزینه = ۰ → اگر ردیفِ خودکاری بود حذفش می‌کند.
    برمی‌گرداند مبلغِ نهاییِ ردیف (۰ یعنی بدونِ ردیف).
    """
    from finance.models import InvoiceLine
    inv = report.invoice
    if not inv:
        return 0
    total = report.content_cost()['total']
    desc = _line_desc(report)
    # ردیفِ موجود: شرحِ جدید، یا شرحِ قدیمیِ همین گزارش (مهاجرت از فرمتِ قبلی)
    legacy_desc = f'{_LEGACY_PREFIX} — گزارش #{report.id}'
    existing = (inv.lines.filter(description=desc).first()
                or inv.lines.filter(description=legacy_desc).first())
    if total <= 0:
        if existing:
            existing.delete()
        return 0
    cat = _content_category(report)
    if existing:
        existing.description = desc
        existing.category = cat
        existing.unit_price = total
        existing.qty = 1
        existing.tax = 0
        existing.discount = 0
        existing.save(update_fields=['description', 'category', 'unit_price', 'qty', 'tax', 'discount'])
    else:
        InvoiceLine.objects.create(
            invoice=inv, order=inv.lines.count(), category=cat,
            description=desc, qty=1, unit_price=total, tax=0, discount=0)
    return total


# سازگاری با کدِ قبلی (اتصالِ فاکتور) — همان sync
def ensure_content_invoice_line(report):
    return sync_content_invoice_line(report)
