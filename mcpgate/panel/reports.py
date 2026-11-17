"""ابزارهای گزارشِ مشتری + تحلیل (آمار سمتِ سرور جمع زده می‌شود؛ فقط نتیجه برمی‌گردد — کم‌مصرف)."""
import re
from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Count, Q, Sum

from mcpgate import journal
from mcpgate.panel import tasks as T
from mcpgate.panel.ctx import MONTHS, Resolver, ToolError, jd, pdate, report_month, table


def _base(gate):
    return getattr(gate, '_base', '').rstrip('/')


def _strip(h, n=400):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', h or '')).strip()[:n] or None


# ───────────── گزارش ─────────────
def reports_query(gate, a):
    from reports.models import Report
    R = Resolver()
    qs = Report.objects.select_related('project').annotate(n=Count('items'))
    if a.get('project'):
        qs = qs.filter(project_id=R.get('project', a['project']))
    if a.get('status'):
        qs = qs.filter(status=a['status'])
    rows = [[r.id, r.title, r.project.name, jd(r.date_from), jd(r.date_to), r.status, r.n, r.is_public]
            for r in qs.order_by('-date_to', '-id')[:int(a.get('limit') or 20)]]
    return table(['id', 'title', 'project', 'from', 'to', 'status', 'items', 'public'], rows)


def report_get(gate, a):
    from reports.models import Report
    r = Report.objects.select_related('project').filter(pk=a.get('id')).first()
    if not r:
        raise ToolError('گزارش پیدا نشد')
    out = {'id': r.id, 'title': r.title, 'project': r.project.name, 'from': jd(r.date_from), 'to': jd(r.date_to),
           'status': r.status, 'public_url': _base(gate) + r.public_url() if r.is_public else None,
           'description': _strip(r.description, 1500), 'items_count': r.items.count()}
    inc = a.get('include') or ['items', 'keywords', 'sections']
    if 'items' in inc:
        rows = []
        for it in r.items.select_related('task__type_def').order_by('order')[:200]:
            t = it.task
            rows.append([it.id, it.task_id, it.override_title or (t.title if t else ''),
                         (t.type_def.name if t and t.type_def_id else it.manual_type) or None,
                         jd(it.override_done_date or (t.done_date if t else None))])
        out['items'] = table(['item', 'task', 'title', 'type', 'done'], rows)
    if 'keywords' in inc:
        out['keywords'] = table(['id', 'keyword', 'position', 'change', 'note'],
                                [[k.id, k.keyword, k.position or None, k.change, k.note or None] for k in r.keywords.all()])
    if 'sections' in inc:
        out['sections'] = table(['id', 'title', 'text'], [[s.id, s.title, _strip(s.description, 300)] for s in r.sections.all()])
    return {k: v for k, v in out.items() if v not in (None, '')}


def _range(a):
    if a.get('month'):
        y, m = report_month(a['month'])
        from core.jalali import j2g
        start = j2g(y, m, 1)
        end = (j2g(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
        return start, end, (y, m)
    if a.get('from') and a.get('to'):
        return pdate(a['from']), pdate(a['to']), None
    raise ToolError('month («1403-07») یا from/to لازم است')


def report_create(gate, a):
    from reports.models import Report, ReportItem
    from tasks.models import Task
    R = Resolver()
    pid = R.get('project', a.get('project'))
    start, end, ym = _range(a)
    title = a.get('title') or (f'گزارش {MONTHS[ym[1] - 1]} {ym[0]}' if ym else 'گزارش جدید')
    mode = a.get('add_tasks', 'done')
    qs = Task.objects.filter(project_id=pid)
    if ym:   # ماهِ گزارش اولویت دارد؛ تسکِ بدونِ ماهِ گزارش با تاریخِ انجام
        qs = qs.filter(Q(report_year=ym[0], report_month=ym[1]) | Q(report_month__isnull=True, done_date__range=(start, end)))
    else:
        qs = qs.filter(Q(done_date__range=(start, end)) | Q(planned_date__range=(start, end)))
    if mode == 'done':
        qs = qs.filter(status='done')
    ids = list(qs.order_by('done_date', 'id').values_list('id', flat=True)) if mode != 'none' else []
    if isinstance(mode, list):
        ids = [int(x) for x in mode]
    if a.get('dry_run'):
        return {'dry_run': True, 'title': title, 'from': jd(start), 'to': jd(end), 'tasks': len(ids)}
    req = T._req(gate)
    with journal.Batch(gate.organization, req.user, 'report_create', title) as b:
        rep = Report.objects.create(project_id=pid, title=title, date_from=start, date_to=end, created_by=req.user,
                                    description=a.get('description') or '')
        journal.note_create(rep)
        for i, tid in enumerate(ids):
            it = ReportItem.objects.create(report=rep, task_id=tid, order=i)
            journal.note_create(it)
    bid = b.id
    return {'id': rep.id, 'title': title, 'items': len(ids), 'batch': bid,
            'edit_url': _base(gate) + rep.get_absolute_url()}


def report_update(gate, a):
    from core.htmlsan import clean_html
    from reports.models import Report, ReportItem, ReportKeyword, ReportSection
    from reports.views import _parse_change
    r = Report.objects.filter(pk=a.get('id')).first()
    if not r:
        raise ToolError('گزارش پیدا نشد')
    req = T._req(gate)
    with journal.Batch(gate.organization, req.user, 'report_update', r.title) as b:
        before = journal.snap(r)
        for k in ('title', 'description'):
            if k in a:
                setattr(r, k, clean_html(a[k]) if k == 'description' else str(a[k])[:200])
        if 'status' in a:
            r.status = a['status']
            r.is_public = r.status == Report.FINAL
        if 'is_public' in a:
            r.is_public = bool(a['is_public'])
        r.save()
        journal.note_update(r, before)
        have = set(r.items.values_list('task_id', flat=True))
        n = r.items.count()
        for tid in a.get('add_tasks') or []:
            if int(tid) not in have:
                journal.note_create(ReportItem.objects.create(report=r, task_id=int(tid), order=n))
                n += 1
        for iid in a.get('remove_items') or []:
            it = r.items.filter(pk=iid).first()
            if it:
                journal.note_hard_delete(it)
                it.delete()
        for kw in a.get('keywords') or []:   # {id?, keyword, position, change, note, delete?}
            obj = r.keywords.filter(pk=kw['id']).first() if kw.get('id') else None
            if obj and kw.get('delete'):
                journal.note_hard_delete(obj)
                obj.delete()
                continue
            kb = journal.snap(obj) if obj else None
            obj = obj or ReportKeyword(report=r, order=r.keywords.count())
            for f in ('keyword', 'position', 'note'):
                if f in kw:
                    setattr(obj, f, str(kw[f] or '')[:200 if f != 'position' else 30])
            if 'change' in kw:
                obj.change = _parse_change(kw['change'])
            obj.save()
            journal.note_update(obj, kb) if kb else journal.note_create(obj)
        for s in a.get('sections') or []:   # {id?, title, description, delete?}
            obj = r.sections.filter(pk=s['id']).first() if s.get('id') else None
            if obj and s.get('delete'):
                journal.note_hard_delete(obj)
                obj.delete()
                continue
            sb = journal.snap(obj) if obj else None
            obj = obj or ReportSection(report=r, order=r.sections.count())
            if 'title' in s:
                obj.title = str(s['title'])[:200]
            if 'description' in s:
                obj.description = clean_html(s['description'])
            obj.save()
            journal.note_update(obj, sb) if sb else journal.note_create(obj)
    bid = b.id
    return {'ok': True, 'batch': bid, 'public_url': _base(gate) + r.public_url() if r.is_public else None}


# ───────────── تحلیل ─────────────
def _jmonth(d):
    from core.jalali import g2j
    j = g2j(d)
    return f'{j.year}-{j.month:02d}'


def _cost(t):
    """هزینهٔ رپورتاژ: فیلدِ سفارشیِ «هزینه» یا فیلدِ قدیمیِ media_cost."""
    if t.type_def_id:
        for f in t.type_def.fields.all():
            if 'هزینه' in f.label:
                v = (t.custom or {}).get(f.key)
                try:
                    return float(v) if v not in (None, '') else 0
                except (TypeError, ValueError):
                    return 0
    return float(t.media_cost or 0)


def stats(gate, a):
    """metric: count|hours|estimate|words|cost|review  ×  by: assignee|project|type|status|month|week|none."""
    from tasks.models import Task
    R = Resolver()
    metric, by = a.get('metric') or 'count', a.get('by') or 'none'
    f = dict(a.get('filter') or {})
    if a.get('period'):   # میان‌بُر: this_month|last_month|last_30|this_year (روی تاریخِ انجام)
        today = date.today()
        from core.jalali import g2j, j2g
        j = g2j(today)
        if a['period'] == 'this_month':
            f.setdefault('done_from', j2g(j.year, j.month, 1).isoformat())
        elif a['period'] == 'last_month':
            y, m = (j.year, j.month - 1) if j.month > 1 else (j.year - 1, 12)
            f.setdefault('done_from', j2g(y, m, 1).isoformat())
            f.setdefault('done_to', (j2g(j.year, j.month, 1) - timedelta(days=1)).isoformat())
        elif a['period'] == 'last_30':
            f.setdefault('done_from', (today - timedelta(days=30)).isoformat())
        elif a['period'] == 'this_year':
            f.setdefault('done_from', j2g(j.year, 1, 1).isoformat())
    qs = T.task_filter(R, f).select_related('project', 'assignee', 'type_def')
    key_attr = {'assignee': ('assignee__full_name', 'assignee'), 'project': ('project__name', 'project'),
                'type': ('type_def__name', 'type'), 'status': ('status', 'status')}
    if metric in ('count', 'hours', 'estimate', 'words') and by in (*key_attr, 'none'):
        agg = {'count': Count('id'), 'hours': Sum('spent_minutes'), 'estimate': Sum('estimate_minutes'),
               'words': Sum('word_count')}[metric]
        if by == 'none':
            v = qs.aggregate(v=agg)['v'] or 0
            return {'metric': metric, 'value': round(v / 60, 1) if metric in ('hours', 'estimate') else v}
        rows = qs.values(key_attr[by][0]).annotate(v=agg).order_by('-v')
        out = [[r[key_attr[by][0]] or '—', round((r['v'] or 0) / 60, 1) if metric in ('hours', 'estimate') else (r['v'] or 0)]
               for r in rows[:int(a.get('limit') or 50)]]
        return table([by, metric], out, total=sum(r[1] for r in out))
    # ماه/هفته/هزینه/بازبینی — جمعِ پایتونی روی دیتای سبک
    if metric == 'cost' or by in ('month', 'week'):
        qs = qs.prefetch_related('type_def__fields')
    groups = defaultdict(float)
    for t in qs:
        d = t.done_date or t.planned_date
        if by == 'month':
            k = f'{t.report_year}-{t.report_month:02d}' if (a.get('month_by') == 'report' and t.report_month) else (_jmonth(d) if d else '—')
        elif by == 'week':
            k = jd(d - timedelta(days=(d.weekday() + 2) % 7)) if d else '—'   # شروعِ هفته = شنبه
        elif by == 'none':
            k = 'all'
        else:
            k = {'assignee': t.assignee.full_name if t.assignee_id else '—', 'project': t.project.name if t.project_id else '—',
                 'type': t.type_def.name if t.type_def_id else t.task_type, 'status': t.status}[by]
        if metric == 'count':
            groups[k] += 1
        elif metric == 'hours':
            groups[k] += (t.spent_minutes or 0) / 60
        elif metric == 'estimate':
            groups[k] += (t.estimate_minutes or 0) / 60
        elif metric == 'words':
            groups[k] += t.word_count or 0
        elif metric == 'cost':
            groups[k] += _cost(t)
        elif metric == 'review':
            groups[k + '|' + (t.review_status or 'unreviewed')] += 1
    if metric == 'review':
        piv = defaultdict(lambda: [0, 0, 0])
        for k, v in groups.items():
            name, st = k.rsplit('|', 1)
            piv[name][{'approved': 0, 'needs_fix': 1}.get(st, 2)] += int(v)
        return table([by, 'approved', 'needs_fix', 'unreviewed'], [[k, *v] for k, v in sorted(piv.items())])
    items = sorted(groups.items(), key=lambda kv: kv[0] if by in ('month', 'week') else -kv[1])
    rows = [[k, round(v, 1) if isinstance(v, float) and not v.is_integer() else int(v)] for k, v in items][:int(a.get('limit') or 60)]
    tot = round(sum(groups.values()), 1)
    return table([by, metric], rows, total=int(tot) if float(tot).is_integer() else tot)


def project_health(gate, a):
    from tasks.models import Task
    R = Resolver()
    pid = R.get('project', a.get('project'))
    from projects.models import Project
    p = Project.objects.get(pk=pid)
    today = date.today()
    months = int(a.get('months') or 3)
    tq = Task.objects.filter(project_id=pid)
    out = {'project': p.name, 'domain': p.domain or None,
           'open': tq.exclude(status__in=['done', 'pending']).count(),
           'overdue': tq.filter(planned_date__lt=today).exclude(status__in=['done', 'pending']).count(),
           'pending_review': tq.filter(status='pending').count(),
           'ideas_no_date': tq.filter(planned_date__isnull=True).exclude(status='done').count()}
    since = today - timedelta(days=31 * months)
    by = defaultdict(lambda: defaultdict(int))
    for t in tq.filter(status='done', done_date__gte=since).select_related('type_def'):
        by[_jmonth(t.done_date)][t.type_def.name if t.type_def_id else t.task_type] += 1
    out['done_by_month'] = {m: dict(v) for m, v in sorted(by.items())}
    sp = tq.filter(done_date__gte=since).aggregate(s=Sum('spent_minutes'))['s'] or 0
    out['hours_last_months'] = round(sp / 60, 1)
    try:
        from finance.balances import project_balance
        out['balance'] = int(project_balance(pid))
    except Exception:  # noqa: BLE001
        pass
    from reports.models import Report
    last = Report.objects.filter(project_id=pid).order_by('-date_to').first()
    out['last_report'] = [last.id, last.title, jd(last.date_to), last.status] if last else None
    try:
        from seo.models import KeywordRankSnapshot, TrackedKeyword
        kws = TrackedKeyword.objects.filter(project_id=pid)
        out['tracked_keywords'] = kws.count()
        snaps = KeywordRankSnapshot.objects.filter(keyword__project_id=pid, date__gte=today - timedelta(days=30))
        if snaps.exists():
            top10 = snaps.filter(position__lte=10).values('keyword').distinct().count()
            out['keywords_top10_last30d'] = top10
    except Exception:  # noqa: BLE001
        pass
    return {k: v for k, v in out.items() if v not in (None, {}, [])}
