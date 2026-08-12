"""ویوهای حسابداری (پایه) — داشبورد، بانک‌ها، بابت‌ها، تراکنش‌ها، ورود اکسل، حقوق."""
import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from core.daterange import DateRangeMixin
from core.jalali import parse_jalali
from projects.models import Project

from .access import FinancePermMixin, require_finance
from .models import (BankAccount, Category, Invoice, InvoiceLine, Payroll,
                     PayrollItem, Transaction)
from .utils import parse_amount, parse_excel_date


def _pj(value):
    """تاریخ شمسی → میلادی؛ خالی/نامعتبر → None."""
    if not value:
        return None
    try:
        return parse_jalali(value)
    except (ValueError, TypeError):
        return None


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


# ── صفحات ────────────────────────────────────────────────────────────────

class FinanceDashboardView(LoginRequiredMixin, FinancePermMixin, DateRangeMixin, TemplateView):
    template_name = 'finance/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_range(self.request)
        ctx.update(self.range_context())
        tx = Transaction.objects.filter(date__range=(start, end))

        income = tx.aggregate(s=Sum('deposit'))['s'] or 0
        expense = tx.aggregate(s=Sum('withdrawal'))['s'] or 0
        banks = list(BankAccount.objects.filter(is_active=True))
        bank_total = sum(b.balance for b in banks)

        # تفکیک بابت: درآمد/هزینه در هر دسته
        cats = []
        for c in Category.objects.all():
            ct = tx.filter(category=c)
            cats.append({
                'name': c.name, 'color': c.color,
                'income': ct.aggregate(s=Sum('deposit'))['s'] or 0,
                'expense': ct.aggregate(s=Sum('withdrawal'))['s'] or 0,
            })

        # حقوق: تعهد کل و پرداختی (کل، مستقل از بازه)
        pay_total = sum(p.total for p in Payroll.objects.all())
        pay_paid = Payroll.objects.aggregate(s=Sum('paid_amount'))['s'] or 0

        ctx.update({
            'income': income, 'expense': expense, 'net': income - expense,
            'banks': banks, 'bank_total': bank_total, 'cats': cats,
            'pay_total': pay_total, 'pay_paid': pay_paid, 'pay_remaining': pay_total - pay_paid,
            'unassigned': tx.filter(project__isnull=True, category__isnull=True).count(),
            'page_title': 'حسابداری',
        })
        return ctx


class TransactionListView(LoginRequiredMixin, FinancePermMixin, DateRangeMixin, TemplateView):
    template_name = 'finance/transactions.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_range(self.request)
        ctx.update(self.range_context())
        g = self.request.GET
        qs = Transaction.objects.select_related('bank_account', 'project', 'category')
        qs = qs.filter(date__range=(start, end))
        if g.get('bank'):
            qs = qs.filter(bank_account_id=g['bank'])
        if g.get('project'):
            qs = qs.filter(project_id=g['project'])
        if g.get('category'):
            qs = qs.filter(category_id=g['category'])
        if g.get('unassigned') == '1':
            qs = qs.filter(project__isnull=True, category__isnull=True)
        ctx['transactions'] = qs[:300]
        ctx['banks'] = BankAccount.objects.filter(is_active=True)
        ctx['projects'] = Project.objects.filter(status=Project.ACTIVE)
        ctx['categories'] = Category.objects.all()
        ctx['filters'] = g
        ctx['page_title'] = 'تراکنش‌ها'
        return ctx


class BankListView(LoginRequiredMixin, FinancePermMixin, TemplateView):
    template_name = 'finance/banks.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['banks'] = BankAccount.objects.all()
        ctx['categories'] = Category.objects.all()
        ctx['page_title'] = 'بانک‌ها'
        return ctx


class ImportView(LoginRequiredMixin, FinancePermMixin, TemplateView):
    template_name = 'finance/import.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['banks'] = BankAccount.objects.filter(is_active=True)
        ctx['page_title'] = 'ورود اکسل'
        return ctx


class PayrollListView(LoginRequiredMixin, FinancePermMixin, TemplateView):
    template_name = 'finance/payroll.html'

    def get_context_data(self, **kwargs):
        from colleagues.models import Colleague
        ctx = super().get_context_data(**kwargs)
        ctx['payrolls'] = Payroll.objects.select_related('colleague').prefetch_related('items')
        ctx['colleagues'] = Colleague.objects.filter(status=Colleague.ACTIVE)
        ctx['page_title'] = 'حقوق'
        return ctx


class InvoiceListView(LoginRequiredMixin, FinancePermMixin, DateRangeMixin, TemplateView):
    template_name = 'finance/invoices.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_range(self.request)
        ctx.update(self.range_context())
        qs = (Invoice.objects.select_related('project')
              .prefetch_related('lines')
              .filter(issue_date__range=(start, end)))
        if self.request.GET.get('project'):
            qs = qs.filter(project_id=self.request.GET['project'])
        ctx['invoices'] = qs
        ctx['projects'] = Project.objects.filter(status=Project.ACTIVE)
        ctx['filters'] = self.request.GET
        ctx['page_title'] = 'فاکتورها'
        return ctx


class InvoiceFormView(LoginRequiredMixin, FinancePermMixin, TemplateView):
    """صفحه‌ی ساخت/ویرایشِ فاکتور (فرمِ کامل با ردیف‌های پویا)."""

    template_name = 'finance/invoice_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pk = kwargs.get('pk')
        invoice = None
        if pk:
            invoice = get_object_or_404(
                Invoice.objects.prefetch_related('lines__category'), pk=pk)
        ctx['invoice'] = invoice
        ctx['lines'] = invoice.lines.all() if invoice else []
        # پیش‌نمایشِ شماره‌ی بعدی برای فاکتورِ جدید
        if not invoice:
            last = Invoice.objects.aggregate(m=Max('number'))['m']
            ctx['next_number'] = (last or 0) + 1
        ctx['projects'] = Project.objects.filter(status=Project.ACTIVE)
        ctx['categories'] = Category.objects.all()
        ctx['page_title'] = f'فاکتور #{invoice.number}' if invoice else 'فاکتور جدید'
        return ctx


# ── API: بانک ─────────────────────────────────────────────────────────────

@login_required
@require_finance
@require_http_methods(['POST'])
def bank_create(request):
    d = _body(request)
    if not d.get('name'):
        return JsonResponse({'detail': 'نام لازم است'}, status=400)
    b = BankAccount.objects.create(
        name=d['name'], bank=d.get('bank', ''), color=d.get('color', '#4183F2'),
        card_number=d.get('card_number', ''), initial_balance=parse_amount(d.get('initial_balance', 0)),
        created_by=request.user)
    return JsonResponse({'id': b.id}, status=201)


@login_required
@require_finance
@require_http_methods(['PATCH', 'DELETE'])
def bank_edit(request, pk):
    b = get_object_or_404(BankAccount, pk=pk)
    if request.method == 'DELETE':
        b.delete()
        return JsonResponse({'ok': True})
    d = _body(request)
    for f in ('name', 'bank', 'color', 'card_number'):
        if f in d:
            setattr(b, f, d[f])
    if 'initial_balance' in d:
        b.initial_balance = parse_amount(d['initial_balance'])
    if 'is_active' in d:
        b.is_active = bool(d['is_active'])
    b.save()
    return JsonResponse({'ok': True})


# ── API: بابت ─────────────────────────────────────────────────────────────

@login_required
@require_finance
@require_http_methods(['POST'])
def category_create(request):
    d = _body(request)
    name = (d.get('name') or '').strip()
    if not name:
        return JsonResponse({'detail': 'عنوان لازم است'}, status=400)
    if Category.objects.filter(name=name).exists():
        return JsonResponse({'detail': 'تکراری است'}, status=400)
    c = Category.objects.create(name=name, color=d.get('color', '#8FA0B8'),
                                is_salary=bool(d.get('is_salary')), order=Category.objects.count())
    return JsonResponse({'id': c.id, 'name': c.name}, status=201)


@login_required
@require_finance
@require_http_methods(['DELETE'])
def category_delete(request, pk):
    get_object_or_404(Category, pk=pk).delete()
    return JsonResponse({'ok': True})


# ── API: تراکنش (ویرایش inline سه ستون + گروهی) ───────────────────────────

@login_required
@require_finance
@require_http_methods(['PATCH'])
def tx_edit(request, pk):
    t = get_object_or_404(Transaction, pk=pk)
    d = _body(request)
    if 'project' in d:
        t.project_id = d['project'] or None
    if 'category' in d:
        t.category_id = d['category'] or None
    if 'note' in d:
        t.note = d['note']
    t.save(update_fields=['project', 'category', 'note', 'updated_at'])
    return JsonResponse({'ok': True})


@login_required
@require_finance
@require_http_methods(['POST'])
def tx_bulk(request):
    d = _body(request)
    ids = d.get('ids', [])
    action = d.get('action')
    qs = Transaction.objects.filter(id__in=ids)
    if action == 'set_project':
        qs.update(project_id=d.get('project') or None)
    elif action == 'set_category':
        qs.update(category_id=d.get('category') or None)
    elif action == 'set_note':
        qs.update(note=d.get('note', ''))
    elif action == 'delete':
        qs.delete()
    else:
        return JsonResponse({'detail': 'action نامعتبر'}, status=400)
    return JsonResponse({'ok': True, 'count': len(ids)})


# ── API: ورود اکسل (پیش‌نمایش + تایید) ────────────────────────────────────

def _parse_workbook(f):
    """ردیف‌های اکسل را می‌خواند. ستون‌ها بر اساس ساختار توافق‌شده:
    ردیف | تاریخ | شرح سند | واریز | برداشت | مانده | توضیحات کاربر.
    ردیف هدر (اولین ردیف غیرعددی) رد می‌شود."""
    from openpyxl import load_workbook
    wb = load_workbook(f, read_only=True, data_only=True)
    ws = wb.active
    rows = []
    for r in ws.iter_rows(values_only=True):
        if r is None or all(c is None for c in r):
            continue
        cells = list(r) + [None] * (7 - len(r))  # حداقل ۷ ستون
        # ستون‌ها: 0=ردیف 1=تاریخ 2=شرح 3=واریز 4=برداشت 5=مانده 6=توضیحات
        d, tm = parse_excel_date(cells[1])
        if d is None:  # ردیف هدر یا نامعتبر
            continue
        rows.append({
            'date': d.isoformat(), 'time': tm,
            'description': str(cells[2] or '').strip(),
            'deposit': parse_amount(cells[3]),
            'withdrawal': parse_amount(cells[4]),
            'balance': parse_amount(cells[5]) if cells[5] not in (None, '') else None,
            'user_note': str(cells[6] or '').strip(),
        })
    return rows


@login_required
@require_finance
@require_http_methods(['POST'])
def import_preview(request):
    import datetime as _dt
    bank_id = request.POST.get('bank')
    f = request.FILES.get('file')
    if not bank_id or not f:
        return JsonResponse({'detail': 'حساب و فایل لازم است'}, status=400)
    try:
        rows = _parse_workbook(f)
    except Exception as e:  # noqa: BLE001
        return JsonResponse({'detail': f'خطا در خواندن فایل: {e}'}, status=400)
    existing = set(Transaction.objects.filter(bank_account_id=bank_id).values_list('import_hash', flat=True))
    new, dup = 0, 0
    for row in rows:
        h = Transaction.make_hash(bank_id, row['date'], row['description'],
                                  row['deposit'], row['withdrawal'], row['balance'])
        row['hash'] = h
        row['dup'] = h in existing
        row['date_fa'] = _fa_date(row['date'])
        dup += row['dup']
        new += not row['dup']
    return JsonResponse({'rows': rows, 'new': new, 'dup': dup})


def _fa_date(iso):
    from core.jalali import format_jalali
    import datetime as _dt
    try:
        return format_jalali(_dt.date.fromisoformat(iso))
    except Exception:  # noqa: BLE001
        return iso


@login_required
@require_finance
@require_http_methods(['POST'])
def import_confirm(request):
    import datetime as _dt
    d = _body(request)
    bank_id = d.get('bank')
    rows = d.get('rows', [])
    bank = get_object_or_404(BankAccount, pk=bank_id)
    existing = set(Transaction.objects.filter(bank_account=bank).values_list('import_hash', flat=True))
    created = 0
    for row in rows:
        h = row.get('hash')
        if not h or h in existing:
            continue
        note = row.get('user_note', '')
        Transaction.objects.create(
            bank_account=bank, date=_dt.date.fromisoformat(row['date']), time=row.get('time', ''),
            description=row.get('description', ''), deposit=row.get('deposit', 0),
            withdrawal=row.get('withdrawal', 0),
            balance=row.get('balance'), user_note=note,
            # ستون «توضیحات کاربر» اکسل مستقیم در فیلد قابل‌ویرایشِ «توضیحات» می‌نشیند
            note=note,
            import_hash=h, created_by=request.user)
        existing.add(h)
        created += 1
    return JsonResponse({'ok': True, 'created': created})


# ── API: حقوق ─────────────────────────────────────────────────────────────

@login_required
@require_finance
@require_http_methods(['POST'])
def payroll_create(request):
    d = _body(request)
    try:
        p, _ = Payroll.objects.get_or_create(
            colleague_id=d['colleague'], year=int(d['year']), month=int(d['month']))
    except (KeyError, ValueError):
        return JsonResponse({'detail': 'همکار/سال/ماه لازم است'}, status=400)
    for it in d.get('items', []):
        if it.get('title'):
            PayrollItem.objects.create(payroll=p, title=it['title'], amount=parse_amount(it.get('amount', 0)))
    return JsonResponse({'id': p.id}, status=201)


@login_required
@require_finance
@require_http_methods(['PATCH', 'DELETE'])
def payroll_edit(request, pk):
    p = get_object_or_404(Payroll, pk=pk)
    if request.method == 'DELETE':
        p.delete()
        return JsonResponse({'ok': True})
    d = _body(request)
    if 'paid_amount' in d:
        p.paid_amount = parse_amount(d['paid_amount'])
    if 'note' in d:
        p.note = d['note']
    p.save()
    return JsonResponse({'ok': True, 'total': p.total, 'remaining': p.remaining, 'status': p.status})


# ── API: فاکتور ───────────────────────────────────────────────────────────

def _parse_qty(value):
    """تعداد را با حفظِ اعشار پارس می‌کند (برخلافِ parse_amount که گرد می‌کند)."""
    from core.jalali import to_en_digits
    import re as _re
    if value in (None, ''):
        return 1
    s = _re.sub(r'[^\d.]', '', to_en_digits(str(value)))
    try:
        return round(float(s), 2) or 1
    except ValueError:
        return 1


def _save_lines(invoice, lines):
    """ردیف‌های فاکتور را از نو می‌سازد (منبع واحد = آرایه‌ی ورودی)."""
    invoice.lines.all().delete()
    for i, li in enumerate(lines):
        # ردیفِ کاملاً خالی را رد کن
        if not (li.get('description') or li.get('category') or
                parse_amount(li.get('unit_price', 0))):
            continue
        InvoiceLine.objects.create(
            invoice=invoice, order=i,
            category_id=li.get('category') or None,
            description=(li.get('description') or '')[:255],
            qty=_parse_qty(li.get('qty', 1)),
            unit_price=parse_amount(li.get('unit_price', 0)),
            tax=parse_amount(li.get('tax', 0)),
            discount=parse_amount(li.get('discount', 0)),
        )


def _invoice_totals(inv):
    return {'subtotal': inv.subtotal, 'tax_total': inv.tax_total,
            'discount_total': inv.discount_total, 'grand_total': inv.grand_total}


@login_required
@require_finance
@require_http_methods(['POST'])
def invoice_create(request):
    d = _body(request)
    issue = _pj(d.get('issue_date'))
    if not issue:
        return JsonResponse({'detail': 'تاریخ ثبت لازم است'}, status=400)
    inv = Invoice.objects.create(
        issue_date=issue, project_id=d.get('project') or None,
        description=(d.get('description') or '').strip(),
        due_date=_pj(d.get('due_date')), created_by=request.user)
    _save_lines(inv, d.get('lines', []))
    return JsonResponse({'id': inv.id, 'number': inv.number}, status=201)


@login_required
@require_finance
@require_http_methods(['PATCH', 'DELETE'])
def invoice_edit(request, pk):
    inv = get_object_or_404(Invoice, pk=pk)
    if request.method == 'DELETE':
        inv.delete()
        return JsonResponse({'ok': True})
    d = _body(request)
    if 'issue_date' in d:
        issue = _pj(d['issue_date'])
        if issue:
            inv.issue_date = issue
    if 'project' in d:
        inv.project_id = d['project'] or None
    if 'description' in d:
        inv.description = (d['description'] or '').strip()
    if 'due_date' in d:
        inv.due_date = _pj(d['due_date'])
    inv.save()
    if 'lines' in d:
        _save_lines(inv, d['lines'])
    return JsonResponse({'ok': True, **_invoice_totals(inv)})
