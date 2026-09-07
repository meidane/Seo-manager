"""منبعِ واحدِ ردیف‌های «گردشِ حسابِ پروژه» (فاکتورها = برداشت، تراکنش‌ها = واریز/برداشت).

قبلاً فقط داخلِ `LedgerView` بود؛ حالا از این‌جا هم `LedgerView` (تبِ گزارشِ حسابداری)، هم
`project_ledger_api` (JSON برای بخشِ «گزارشِ مالیِ پروژه» زیرِ فاکتور و در صفحه‌ی گزارش)
می‌خوانند. منطق را جای دیگر تکرار نکن.

**مانده همیشه کلی است، نه بازه‌ای:** مانده‌ی تجمعیِ هر ردیف و مانده‌ی نهایی روی **کلِ
تاریخ** حساب می‌شوند (همان `balances.project_balance`)، حتی وقتی فقط بازه‌ای از ردیف‌ها
نمایش داده می‌شود — تا با ماندهٔ فاکتور/گزارش یکی باشد (خواستِ کاربر).
"""
from datetime import date, timedelta

from django.db.models import Q

from core.jalali import format_jalali

from .models import Invoice, Transaction


def last_3_months_range(today=None):
    """بازه‌ی پیش‌فرضِ «۳ ماهِ اخیر» (میلادی) — امروز و ۹۰ روزِ قبلش."""
    today = today or date.today()
    return today - timedelta(days=90), today


def _all_rows(project_id):
    """همه‌ی ردیف‌های گردشِ حسابِ پروژه (بدونِ فیلترِ بازه) — برای مانده‌ی تجمعیِ درست."""
    rows = []

    def _tx_cats(t):
        return '، '.join(c.name for c in t.categories.all())

    inv_qs = Invoice.objects.filter(project_id=project_id).prefetch_related('lines__category')
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

    tx = (Transaction.objects.select_related('bank_account')
          .prefetch_related('categories', 'splits__category')
          .filter(Q(project_id=project_id) | Q(splits__project_id=project_id)).distinct())
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
    return rows


def project_ledger(project_id, start=None, end=None):
    """ردیف‌های گردشِ حسابِ پروژه به‌همراهِ جمع‌ها.

    مانده‌ی تجمعی روی **کلِ تاریخ** حساب می‌شود (نه فقط بازه)؛ اگر بازه داده شود فقط
    ردیف‌های همان بازه **نمایش** داده می‌شوند ولی ماندهٔ هر ردیف همان ماندهٔ واقعیِ
    تجمعیِ کل است. برمی‌گرداند dict:
    `rows` (جدید→قدیم، هر ردیف `balance`/`date_fa`)، `total_deposit`/`total_withdrawal`
    (فقط ردیف‌های نمایش‌داده‌شده)، `final_balance` (**مانده‌ی کلیِ پروژه**، نه بازه‌ای).
    """
    rows = _all_rows(project_id)
    rows.sort(key=lambda r: r['date'])
    bal = 0
    for r in rows:
        bal += r['deposit'] - r['withdrawal']
        r['balance'] = bal            # مانده‌ی تجمعیِ کل (درست حتی در نمای بازه‌ای)
        r['date_fa'] = format_jalali(r['date'])
    global_balance = bal              # = balances.project_balance

    # فیلترِ نمایش به بازه (اختیاری) — مانده‌ها دست‌نخورده می‌مانند
    if start and end:
        disp = [r for r in rows if start <= r['date'] <= end]
    else:
        disp = list(rows)
    tot_d = sum(r['deposit'] for r in disp)
    tot_w = sum(r['withdrawal'] for r in disp)
    disp.reverse()  # جدید → قدیم

    return {'rows': disp, 'total_deposit': tot_d,
            'total_withdrawal': tot_w, 'final_balance': global_balance}
