"""ابزارهای تراکنشِ MCPِ پنل — **فقط پیشنهاد** (به خواستِ کاربر ثبتِ مستقیم نداریم): `tx_suggest` یک `TxSuggestion`
با منبعِ «MCP» می‌سازد که در جدولِ تراکنش‌ها کنارِ پیشنهادِ حافظه دیده و با یک کلیک تأیید/رد می‌شود."""
from collections import defaultdict

from django.db.models import Q, Sum

from mcpgate import journal
from mcpgate.panel.ctx import Resolver, ToolError, jd, pdate, table


def _dir(t):
    return 'in' if (t.deposit or 0) > 0 else 'out'


def _amt(t):
    return int((t.deposit or 0) + (t.withdrawal or 0))


def tx_queue(gate, a):
    from finance.models import Transaction, TxSuggestion
    from finance.tx_suggest import unassigned_qs
    qs = unassigned_qs().select_related('bank_account')
    if not a.get('include_suggested'):
        qs = qs.exclude(suggestion__status=TxSuggestion.PENDING)
    if a.get('bank'):
        qs = qs.filter(Q(bank_account_id=a['bank']) if str(a['bank']).isdigit() else Q(bank_account__name__icontains=a['bank']))
    total = qs.count()
    lim, off = min(int(a.get('limit') or 30), 100), int(a.get('offset') or 0)
    rows = [[t.id, jd(t.date), t.bank_account.name, _dir(t), _amt(t), (t.description or '')[:140], t.note or None]
            for t in qs.order_by('-date', '-id')[off:off + lim]]
    out = table(['id', 'date', 'bank', 'dir', 'amount', 'desc', 'note'], rows, total=total,
                next_offset=off + lim if off + lim < total else None)
    if off == 0:   # فقط بارِ اول: نمونهٔ تخصیص‌های قبلی تا الگو دستِ هوش مصنوعی بیاید
        ex = (Transaction.objects.filter(Q(project__isnull=False) | Q(categories__isnull=False)).distinct()
              .select_related('project').prefetch_related('categories').order_by('-date')[:40])
        out['examples'] = table(['dir', 'amount', 'desc', 'project', 'categories', 'note'],
                                [[_dir(t), _amt(t), (t.description or '')[:70], t.project.name if t.project_id else None,
                                  [c.name for c in t.categories.all()] or None, t.note or None] for t in ex])
        out['next'] = 'برای هر تراکنش با tx_suggest پیشنهاد بده (project/categories با نام؛ note کوتاه؛ why یک خط). مطمئن نبودی، رد شو.'
    return out


def tx_suggest(gate, a):
    from finance.models import Transaction, TxSuggestion
    from mcpgate.panel.ctx import fake_request
    items = a.get('items') or []
    if not items:
        raise ToolError('items خالی است')
    R = Resolver()
    made, errors = 0, []
    with journal.Batch(gate.organization, fake_request(gate).user, 'tx_suggest', f'{len(items)} پیشنهاد') as b:
        for it in items[:300]:
            try:
                t = Transaction.objects.filter(pk=it.get('id')).first()
                if not t:
                    raise ToolError('تراکنش نیست')
                if t.project_id or t.categories.exists() or t.splits.exists():
                    raise ToolError('از قبل تخصیص دارد')
                pid = R.get('project', it.get('project')) if it.get('project') else None
                cats = [R.get('category', c) for c in (it.get('categories') or ([it['category']] if it.get('category') else []))]
                if not pid and not cats and not it.get('note'):
                    raise ToolError('پیشنهادِ خالی')
                s = TxSuggestion.objects.filter(transaction=t).first()
                before = journal.snap(s) if s else None
                s = s or TxSuggestion(transaction=t)
                s.source, s.project_id, s.categories = TxSuggestion.MCP, pid, cats
                s.note, s.why, s.refs = str(it.get('note') or '')[:255], str(it.get('why') or '')[:500], []
                s.status, s.decided_at, s.decided_by = TxSuggestion.PENDING, None, None
                s.save()
                journal.note_update(s, before) if before else journal.note_create(s)
                made += 1
            except ToolError as e:
                errors.append([it.get('id'), str(e)])
    bid = b.id
    out = {'suggested': made, 'batch': bid, 'note': 'در جدولِ تراکنش‌های پنل با برچسبِ MCP منتظرِ تأییدِ کاربر است.'}
    if errors:
        out['errors'] = table(['id', 'error'], errors[:30])
    return out


def tx_query(gate, a):
    from finance.models import Transaction
    R = Resolver()
    qs = Transaction.objects.select_related('bank_account', 'project').prefetch_related('categories')
    if a.get('q'):
        qs = qs.filter(Q(description__icontains=a['q']) | Q(note__icontains=a['q']))
    if a.get('project'):
        qs = qs.filter(Q(project_id=R.get('project', a['project'])) | Q(splits__project_id=R.get('project', a['project'])))
    if a.get('category'):
        qs = qs.filter(categories__id=R.get('category', a['category']))
    if a.get('bank'):
        qs = qs.filter(Q(bank_account_id=a['bank']) if str(a['bank']).isdigit() else Q(bank_account__name__icontains=a['bank']))
    if a.get('from'):
        qs = qs.filter(date__gte=pdate(a['from']))
    if a.get('to'):
        qs = qs.filter(date__lte=pdate(a['to']))
    if a.get('kind') == 'in':
        qs = qs.filter(deposit__gt=0)
    elif a.get('kind') == 'out':
        qs = qs.filter(withdrawal__gt=0)
    if a.get('unassigned'):
        qs = qs.filter(project__isnull=True, categories__isnull=True, splits__isnull=True)
    if a.get('min'):
        qs = qs.filter(Q(deposit__gte=a['min']) | Q(withdrawal__gte=a['min']))
    if a.get('max'):
        qs = qs.filter(deposit__lte=a['max'], withdrawal__lte=a['max'])
    qs = qs.distinct()
    agg = qs.aggregate(dep=Sum('deposit'), wd=Sum('withdrawal'))
    total = qs.count()
    lim, off = min(int(a.get('limit') or 30), 200), int(a.get('offset') or 0)
    rows = [[t.id, jd(t.date), t.bank_account.name, _dir(t), _amt(t), (t.description or '')[:100],
             t.project.name if t.project_id else None, [c.name for c in t.categories.all()] or None, t.note or None]
            for t in qs.order_by('-date', '-id')[off:off + lim]]
    return table(['id', 'date', 'bank', 'dir', 'amount', 'desc', 'project', 'categories', 'note'], rows, total=total,
                 sum_in=int(agg['dep'] or 0), sum_out=int(agg['wd'] or 0), next_offset=off + lim if off + lim < total else None)


def finance_stats(gate, a):
    """جمعِ واریز/برداشت بر اساسِ category|project|month|bank (+ جمعِ فاکتورها برای project/category)."""
    from finance.models import InvoiceLine, Transaction
    from core.jalali import g2j
    R = Resolver()
    by = a.get('by') or 'category'
    qs = Transaction.objects.all()
    if a.get('from'):
        qs = qs.filter(date__gte=pdate(a['from']))
    if a.get('to'):
        qs = qs.filter(date__lte=pdate(a['to']))
    if a.get('project'):
        qs = qs.filter(project_id=R.get('project', a['project']))
    g = defaultdict(lambda: [0, 0, 0])   # [in, out, invoice]
    if by in ('category', 'project', 'bank'):
        key = {'category': 'categories__name', 'project': 'project__name', 'bank': 'bank_account__name'}[by]
        for r in qs.values(key).annotate(i=Sum('deposit'), o=Sum('withdrawal')):
            g[r[key] or '—'][0] += int(r['i'] or 0)
            g[r[key] or '—'][1] += int(r['o'] or 0)
        if by in ('category', 'project'):
            lq = InvoiceLine.objects.all()
            if a.get('from'):
                lq = lq.filter(invoice__issue_date__gte=pdate(a['from']))
            if a.get('to'):
                lq = lq.filter(invoice__issue_date__lte=pdate(a['to']))
            if a.get('project'):
                lq = lq.filter(invoice__project_id=R.get('project', a['project']))
            k2 = 'category__name' if by == 'category' else 'invoice__project__name'
            for li in lq.select_related('category', 'invoice__project'):
                name = (li.category.name if by == 'category' and li.category_id else
                        li.invoice.project.name if by == 'project' and li.invoice.project_id else '—')
                g[name][2] += int(li.total or 0)
            _ = k2
    elif by == 'month':
        for t in qs.only('date', 'deposit', 'withdrawal'):
            j = g2j(t.date)
            k = f'{j.year}-{j.month:02d}'
            g[k][0] += int(t.deposit or 0)
            g[k][1] += int(t.withdrawal or 0)
    else:
        raise ToolError('by: category|project|month|bank')
    rows = sorted(([k, *v, v[0] - v[1]] for k, v in g.items()), key=lambda r: r[0] if by == 'month' else -(r[1] + r[2]))
    return table([by, 'in', 'out', 'invoiced', 'net'], rows)
