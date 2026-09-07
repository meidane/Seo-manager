"""منبعِ واحدِ ردیف‌های «گردشِ حسابِ پروژه» (فاکتورها = برداشت، تراکنش‌ها = واریز/برداشت).

قبلاً فقط داخلِ `LedgerView` بود؛ حالا از این‌جا هم `LedgerView` (تبِ گزارشِ حسابداری)، هم
`project_ledger_api` (JSON برای بخشِ «گزارشِ مالیِ پروژه» زیرِ فاکتور و در صفحه‌ی گزارش)
می‌خوانند. منطق را جای دیگر تکرار نکن.
"""
from datetime import date

from django.db.models import Q

from core.jalali import format_jalali

from .models import Invoice, Transaction


def last_3_months_range(today=None):
    """بازه‌ی پیش‌فرضِ «۳ ماهِ اخیر» (میلادی) — امروز و ۹۰ روزِ قبلش."""
    today = today or date.today()
    from datetime import timedelta
    return today - timedelta(days=90), today


def project_ledger(project_id, start=None, end=None):
    """ردیف‌های گردشِ حسابِ پروژه به‌همراهِ جمع‌ها.

    برمی‌گرداند dict: `rows` (جدید→قدیم، هر ردیف `balance`/`date_fa` دارد)،
    `total_deposit`, `total_withdrawal`, `final_balance`.
    بازه اختیاری است؛ اگر داده نشود همه‌ی تاریخ می‌آید.
    """
    rows = []

    def _tx_cats(t):
        return '، '.join(c.name for c in t.categories.all())

    # فاکتورهای پروژه → برداشت (با ریزِ ردیف‌ها برای بازشدن)
    inv_qs = Invoice.objects.filter(project_id=project_id).prefetch_related('lines__category')
    if start and end:
        inv_qs = inv_qs.filter(issue_date__range=(start, end))
    for inv in inv_qs:
        lines = list(inv.lines.all())
        cats = sorted({li.category.name for li in lines if li.category_id})
        rows.append({
            'date': inv.issue_date,
            'title': f'فاکتور #{inv.number}' + (f' — {inv.description}' if inv.description else ''),
            'kind': 'invoice', 'ref_id': inv.id,
            'deposit': 0, 'withdrawal': int(inv.grand_total), 'bank': '',
            'cat': '، '.join(cats),
            'lines': [{'cat': (li.category.name if li.category_id else '—'),
                       'desc': li.description, 'qty': int(li.qty),
                       'unit': int(li.unit_price), 'total': int(li.total)} for li in lines],
        })

    # تراکنش‌های پروژه یا اسپلیت‌های همین پروژه → واریز/برداشت
    tx = (Transaction.objects.select_related('bank_account')
          .prefetch_related('categories', 'splits__category')
          .filter(Q(project_id=project_id) | Q(splits__project_id=project_id)).distinct())
    if start and end:
        tx = tx.filter(date__range=(start, end))
    for t in tx:
        splits = list(t.splits.all())
        if splits:
            for s in splits:
                if str(s.project_id) != str(project_id):
                    continue
                amt = int(s.amount or 0)
                rows.append({
                    'date': t.date, 'title': (s.note or t.description or '—') + ' — تفکیک',
                    'kind': 'tx', 'ref_id': t.id, 'split': True,
                    'deposit': amt if t.deposit else 0,
                    'withdrawal': amt if t.withdrawal else 0,
                    'bank': t.bank_account.name if t.bank_account_id else '',
                    'cat': s.category.name if s.category_id else '',
                })
        elif str(t.project_id) == str(project_id):
            rows.append({
                'date': t.date, 'title': t.description or '—',
                'kind': 'tx', 'ref_id': t.id,
                'deposit': int(t.deposit or 0), 'withdrawal': int(t.withdrawal or 0),
                'bank': t.bank_account.name if t.bank_account_id else '',
                'cat': _tx_cats(t),
            })

    # مانده‌ی تجمعی به ترتیبِ تاریخِ صعودی، سپس نمایش نزول (جدید→قدیم)
    rows.sort(key=lambda r: r['date'])
    bal = tot_d = tot_w = 0
    for r in rows:
        bal += r['deposit'] - r['withdrawal']
        r['balance'] = bal
        r['date_fa'] = format_jalali(r['date'])
        tot_d += r['deposit']
        tot_w += r['withdrawal']
    rows.reverse()

    return {'rows': rows, 'total_deposit': tot_d,
            'total_withdrawal': tot_w, 'final_balance': bal}
