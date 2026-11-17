"""ایندکس: _status/_custom_value (کمکی) · task_filter (فیلترِ مشترک) · tasks_query/task_get (خواندن) ·
_build/_save_one/_summary/tasks_save/tasks_update_where/tasks_delete/tasks_restore (نوشتن) · task_comment/task_review ·
projects_query/project_get/project_save (پروژه).

ابزارهای تسک/پروژهٔ MCPِ پنل. همهٔ نوشتن‌ها از `tasks.api.apply_fields` (منبعِ واحدِ ذخیره) می‌گذرند،
در تاریخچهٔ تسک با برچسبِ MCP ثبت می‌شوند و در ژورنال (قابلِ بازگردانی) می‌روند.

ردیفِ ورودیِ تسک (`tasks_save`/`import_tasks`) — همه اختیاری جز title/project در ساخت:
  id, title, project (نام/دامنه/id), assignee (نام/یوزرنیم/id), type (نام/id), status (todo|doing|pending|done),
  planned (تاریخ)، done (تاریخ)، deadline، estimate («1:30»/دقیقه)، report_month («1403-07»/«مهر 1403»/none)،
  description، checklist ([متن] یا [{text,done}])، needs_review، fields ({برچسب یا key: مقدار})، link (لینکِ صفحه/رپورتاژ).
"""
import re

from django.db.models import Q
from django.utils import timezone

from mcpgate import journal
from mcpgate.panel.ctx import Resolver, ToolError, jd, minutes, pdate, report_month, table

STATUS = {'todo': 'todo', 'doing': 'doing', 'pending': 'pending', 'done': 'done',
          'انجام شده': 'done', 'انجام‌شده': 'done', 'در حال انجام': 'doing', 'در انتظار': 'todo'}


def _status(v):
    if v in (None, ''):
        return None
    s = str(v).strip().lower()
    if s not in STATUS:
        raise ToolError(f'وضعیتِ نامعتبر: {v} (todo|doing|pending|done)')
    return STATUS[s]


def _type_fields(td):
    """{نرمالِ برچسب یا key: field}"""
    out = {}
    for f in td.fields.all():
        out[f.key] = f
        out[re.sub(r'\s+', ' ', f.label.strip())] = f
    return out


def _custom_value(f, v):
    if v is None:
        return None
    if f.kind == f.TAGS:
        return [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else \
            [w.strip() for w in re.split(r'[-،,\n]', str(v)) if w.strip()]
    if f.kind == f.TEXTAREA and isinstance(v, list):
        return '\n'.join(str(x).strip() for x in v if str(x).strip())
    if f.kind == f.NUMBER:
        from core.jalali import to_en_digits
        s = re.sub(r'[^\d.\-]', '', to_en_digits(str(v)))
        return (float(s) if '.' in s else int(s)) if s not in ('', '-', '.') else None
    return str(v).strip()


def _page_link_field(td):
    return next((f for f in td.fields.all() if f.is_page_link), None) if td else None


def _norm_url(u):
    u = (u or '').strip().lower()
    u = re.sub(r'^https?://(www\.)?', '', u)
    from urllib.parse import unquote
    return unquote(u).rstrip('/')


# ───────────── خواندن ─────────────
DEFAULT_COLS = ['id', 'title', 'project', 'assignee', 'type', 'status', 'planned', 'done', 'rm']
EXTRA_COLS = {'description', 'estimate', 'spent', 'deadline', 'review', 'words', 'fields', 'needs_review', 'link'}


def task_filter(R, f, qs=None):
    """فیلترِ مشترکِ query/update_where/delete/stats."""
    from tasks.models import Task
    qs = qs if qs is not None else Task.objects.all()
    f = f or {}
    if f.get('ids'):
        qs = qs.filter(id__in=[int(x) for x in f['ids']])
    if f.get('project'):
        ps = f['project'] if isinstance(f['project'], list) else [f['project']]
        qs = qs.filter(project_id__in=[R.get('project', p) for p in ps])
    if f.get('assignee'):
        a = f['assignee']
        qs = qs.filter(assignee__isnull=True) if a in ('none', 'بدون') else qs.filter(assignee_id=R.get('colleague', a))
    if f.get('type'):
        ts = f['type'] if isinstance(f['type'], list) else [f['type']]
        qs = qs.filter(type_def_id__in=[R.get('type', t) for t in ts])
    if f.get('status'):
        ss = f['status'] if isinstance(f['status'], list) else [f['status']]
        qs = qs.filter(status__in=[_status(s) for s in ss])
    if f.get('from'):
        qs = qs.filter(planned_date__gte=pdate(f['from']))
    if f.get('to'):
        qs = qs.filter(planned_date__lte=pdate(f['to']))
    if f.get('done_from'):
        qs = qs.filter(done_date__gte=pdate(f['done_from']))
    if f.get('done_to'):
        qs = qs.filter(done_date__lte=pdate(f['done_to']))
    if 'report_month' in f and f['report_month'] not in (None, ''):
        y, m = report_month(f['report_month'])
        qs = qs.filter(report_month__isnull=True) if m is None else qs.filter(report_year=y, report_month=m)
    if f.get('q'):
        q = str(f['q'])
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(custom__icontains=q))
    if f.get('overdue'):
        from datetime import date
        qs = qs.filter(planned_date__lt=date.today()).exclude(status__in=['done', 'pending'])
    if f.get('no_date'):
        qs = qs.filter(planned_date__isnull=True)
    return qs


def _row(t, cols):
    out = []
    for c in cols:
        if c == 'id':
            out.append(t.id)
        elif c == 'title':
            out.append(t.title)
        elif c == 'project':
            out.append(t.project.name if t.project_id else None)
        elif c == 'assignee':
            out.append(t.assignee.full_name if t.assignee_id else None)
        elif c == 'type':
            out.append(t.type_def.name if t.type_def_id else t.task_type)
        elif c == 'status':
            out.append(t.status)
        elif c == 'planned':
            out.append(jd(t.planned_date))
        elif c == 'done':
            out.append(jd(t.done_date))
        elif c == 'rm':
            out.append(f'{t.report_year}-{t.report_month:02d}' if t.report_month else None)
        elif c == 'description':
            txt = re.sub(r'<[^>]+>', ' ', t.description or '')
            txt = re.sub(r'\s+', ' ', txt).strip()
            out.append(txt[:300] or None)
        elif c == 'estimate':
            out.append(t.estimate_minutes)
        elif c == 'spent':
            out.append(t.spent_minutes or None)
        elif c == 'deadline':
            out.append(jd(t.deadline))
        elif c == 'review':
            out.append(t.review_status if t.review_status != 'unreviewed' else None)
        elif c == 'words':
            out.append(t.word_count)
        elif c == 'needs_review':
            out.append(t.needs_review)
        elif c == 'link':
            out.append(getattr(t, 'page_link', '') or None)
        elif c == 'fields':
            fs = {}
            if t.type_def_id:
                for f in t.type_def.fields.all():
                    v = (t.custom or {}).get(f.key)
                    if v not in (None, '', []):
                        fs[f.label] = v
            out.append(fs or None)
    return out


def tasks_query(gate, a):
    R = Resolver()
    from tasks.models import Task
    base = Task.objects.deleted() if a.get('deleted') else Task.objects.all()
    qs = task_filter(R, a, base).select_related('project', 'assignee', 'type_def').prefetch_related('type_def__fields')
    total = qs.count()
    if a.get('count_only'):
        return {'total': total}
    order = {'planned': 'planned_date', '-planned': '-planned_date', 'done': 'done_date', '-done': '-done_date',
             'id': 'id', '-id': '-id'}.get(a.get('order') or '-planned', '-planned_date')
    lim, off = min(int(a.get('limit') or 20), 200), int(a.get('offset') or 0)
    cols = DEFAULT_COLS + [c for c in (a.get('fields') or []) if c in EXTRA_COLS]
    rows = [_row(t, cols) for t in qs.order_by(order, '-id')[off:off + lim]]
    return table(cols, rows, total=total, next_offset=off + lim if off + lim < total else None)


def task_get(gate, a):
    from tasks.models import Task
    t = Task.all_objects.select_related('project', 'assignee', 'type_def').filter(pk=a.get('id')).first()
    if not t:
        raise ToolError('تسک پیدا نشد')
    cols = DEFAULT_COLS + ['description', 'estimate', 'spent', 'deadline', 'review', 'needs_review', 'words', 'link', 'fields']
    out = dict(zip(cols, _row(t, cols)))
    out['description'] = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t.description or '')).strip()[:3000] or None
    out['checklist'] = t.checklist or None
    out['deleted'] = bool(t.deleted_at)
    out['recurring'] = bool(t.recurrence_id)
    inc = a.get('include') or []
    if 'history' in inc:
        out['history'] = [[jd(h.created_at), h.get_action_display(), h.source or None, h.changes or None]
                          for h in t.history.all()[:15]]
    if 'comments' in inc:
        out['comments'] = [[jd(c.created_at), str(c.author) if c.author_id else '',
                            re.sub(r'<[^>]+>', ' ', c.body)[:500]] for c in t.comments.select_related('author')[:15]]
    return {k: v for k, v in out.items() if v not in (None, [], {}, '')}


# ───────────── نوشتن ─────────────
def _build(gate, req, R, item, defaults, task=None):
    """یک ردیف → (task آمادهٔ ذخیره، data برای apply_fields). ذخیره نمی‌کند."""
    from tasks.api import apply_fields
    from tasks.models import Task, TaskTypeDef
    it = {**(defaults or {}), **{k: v for k, v in item.items() if v is not None}}
    new = task is None
    if new:
        if not it.get('title'):
            raise ToolError('title لازم است')
        if not it.get('project'):
            raise ToolError('project لازم است')
        task = Task(created_by=req.user, planned_date=None)
        if not it.get('type'):   # بدونِ نوع → «سایر» (نه نوعِ قدیمیِ پیش‌فرضِ مدل)
            other = TaskTypeDef.objects.filter(builtin_key='other').first()
            if other:
                it['type'] = other.id
    data = {}
    if 'title' in it:
        data['title'] = str(it['title']).strip()[:255]
    if 'project' in it:
        data['project'] = R.get('project', it['project'])
    if 'assignee' in it:
        data['assignee'] = R.get('colleague', it['assignee']) if it['assignee'] not in ('none', '') else None
    td = task.type_def if task.type_def_id else None
    if it.get('type'):
        data['type_def'] = R.get('type', it['type'])
        td = TaskTypeDef.objects.prefetch_related('fields').get(pk=data['type_def'])
    if 'status' in it:
        data['status'] = _status(it['status'])
    if 'description' in it:
        d = str(it['description'] or '')
        data['description'] = d if '<' in d else ''.join(f'<p>{p}</p>' for p in d.split('\n') if p.strip())
    if 'checklist' in it and isinstance(it['checklist'], list):
        data['checklist'] = [x if isinstance(x, dict) else {'text': str(x), 'done': False} for x in it['checklist']]
    if 'needs_review' in it:
        data['needs_review'] = bool(it['needs_review'])
    if 'estimate' in it:
        data['estimate_minutes'] = minutes(it['estimate'])
    if 'report_month' in it:
        y, m = report_month(it['report_month'])
        data['report_year'], data['report_month'] = y, m
    if new and 'needs_review' not in data:   # پیش‌فرض = تنظیمِ مسئول یا «نیاز به بازبینی»ِ نوع (مثلِ مودال)
        from colleagues.models import Colleague
        c = Colleague.objects.filter(pk=data['assignee']).first() if data.get('assignee') else None
        data['needs_review'] = bool((c and c.needs_review) or (td and td.requires_review))
    # فیلدهای سفارشیِ نوع (با برچسب یا key) + `link` → فیلدِ «لینکِ صفحه»ی نوع
    fields = dict(it.get('fields') or {})
    if it.get('link') and td:
        pl = _page_link_field(td)
        if pl:
            fields.setdefault(pl.key, it['link'])
    if fields:
        if not td:
            raise ToolError('برای fields اول type را مشخص کن')
        fmap = _type_fields(td)
        patch = {}
        for k, v in fields.items():
            f = fmap.get(k) or fmap.get(re.sub(r'\s+', ' ', str(k).strip()))
            if not f:
                raise ToolError(f'فیلدِ «{k}» در نوعِ «{td.name}» نیست. موجود: {"، ".join(x.label for x in td.fields.all())}')
            patch[f.key] = _custom_value(f, v)
        data['custom_patch'] = patch
    apply_fields(task, data, req)
    # تاریخ‌ها مستقیم (ISO یا شمسی)
    if 'planned' in it:
        task.planned_date = pdate(it['planned'])
    if 'deadline' in it:
        task.deadline = pdate(it['deadline'])
    if 'done' in it:
        task.done_date = pdate(it['done'])
        if task.done_date and task.status not in ('done', 'pending') and 'status' not in it:
            task.status = 'done'
    if task.status == 'done' and not task.done_date:
        task.done_date = task.planned_date or timezone.localdate()
    if task.done_date and not task.planned_date:
        task.planned_date = task.done_date
    # ماهِ گزارش خودکار از تاریخ (اگر صریح نیامد و ماهِ گزارشِ آن تاریخ تعریف شده)
    if new and 'report_month' not in it and (task.done_date or task.planned_date) and defaults.get('auto_report_month', True):
        from core.jalali import g2j
        from tasks.models import ReportPeriod
        j = g2j(task.done_date or task.planned_date)
        if ReportPeriod.objects.filter(year=j.year, month=j.month).exists():
            task.report_year, task.report_month = j.year, j.month
    return task


def _save_one(gate, req, R, item, defaults, dry_run):
    """(op, task|None, پیام) — op: create/update/skip/error"""
    from tasks import history as th
    from tasks.api import _custom_fields_error, _publish_url_error
    from tasks.models import Task, TaskHistory
    existing = None
    if item.get('id'):
        existing = Task.all_objects.select_related('type_def').filter(pk=item['id']).first()
        if not existing:
            return 'error', None, f'تسکِ #{item["id"]} نیست'
    before = journal.snap(existing) if existing else None
    hist_before = th.snapshot(existing) if existing else None
    task = _build(gate, req, R, item, defaults, existing)
    err = _publish_url_error(task) or _custom_fields_error(task)
    if err:
        return 'error', task, err
    if dry_run:
        return ('update' if existing else 'create'), task, ''
    task.save()
    if existing:
        changes = th.diff(task, hist_before)
        if journal.note_update(task, before):
            th.record(task, TaskHistory.UPDATED, req.user, changes)
            return 'update', task, ''
        return 'same', task, ''
    th.record(task, TaskHistory.CREATED, req.user)
    journal.note_create(task)
    return 'create', task, ''


def _summary(results, dry_run, batch_id=None, max_examples=5, rows_idx=None):
    cnt = {}
    errors, examples = [], []
    for n, (op, task, msg) in enumerate(results):
        i = rows_idx[n] if rows_idx else n
        cnt[op] = cnt.get(op, 0) + 1
        if op == 'error':
            errors.append([i, (task.title if task else ''), msg])
        elif len(examples) < max_examples and op in ('create', 'update'):
            examples.append([i, op, task.id, task.title, task.project.name if task.project_id else None,
                             jd(task.done_date or task.planned_date)])
    out = {'dry_run': dry_run, 'counts': cnt, 'examples': table(['row', 'op', 'id', 'title', 'project', 'date'], examples)}
    if errors:
        out['errors'] = table(['row', 'title', 'error'], errors[:30])
    if batch_id:
        out['batch'] = batch_id
        out['undo'] = f'undo(batch={batch_id})'
    if dry_run:
        out['next'] = 'اگر درست است همین را با dry_run=false بفرست'
    return out


def tasks_save(gate, a, tool='tasks_save'):
    items = a.get('items') or []
    if not items:
        raise ToolError('items خالی است')
    if len(items) > 500:
        raise ToolError('حداکثر ۵۰۰ ردیف در هر فراخوانی')
    dry = a.get('dry_run', False)
    req, R = _req(gate), Resolver()
    defaults = a.get('defaults') or {}
    results = []
    with journal.Batch(gate.organization, req.user, tool, f'{len(items)} ردیف') as b:
        for item in items:
            try:
                results.append(_save_one(gate, req, R, item, defaults, dry))
            except ToolError as e:
                results.append(('error', None, str(e)))
    bid = b.id
    return _summary(results, dry, None if dry else bid)


def _req(gate):
    from mcpgate.panel.ctx import fake_request
    return fake_request(gate)


def tasks_update_where(gate, a):
    R = Resolver()
    qs = task_filter(R, a.get('filter') or {})
    ids = list(qs.values_list('id', flat=True)[:1000])
    if not ids:
        return {'matched': 0}
    if not a.get('set'):
        raise ToolError('set لازم است')
    items = [{**a['set'], 'id': i} for i in ids]
    out = tasks_save(gate, {'items': items, 'dry_run': a.get('dry_run', True)}, 'tasks_update_where')
    out['matched'] = len(ids)
    return out


def tasks_delete(gate, a):
    """حذفِ نرم (به سطلِ زباله) — با undo یا tasks_restore برمی‌گردد."""
    from tasks import history as th
    from tasks.api import _stop_timer
    from tasks.models import Task, TaskHistory
    R = Resolver()
    qs = task_filter(R, a.get('filter') or {'ids': a.get('ids') or []}) if (a.get('filter') or a.get('ids')) else None
    if qs is None:
        raise ToolError('ids یا filter لازم است')
    tasks = list(qs[:1000])
    if a.get('dry_run', True):
        return {'dry_run': True, 'matched': len(tasks), 'examples': [[t.id, t.title] for t in tasks[:5]],
                'next': 'برای حذف dry_run=false'}
    req = _req(gate)
    with journal.Batch(gate.organization, req.user, 'tasks_delete', f'{len(tasks)} تسک') as b:
        for t in tasks:
            before = journal.snap(t)
            _stop_timer(t)
            t.deleted_at, t.deleted_by = timezone.now(), req.user
            t.save()
            journal.note_update(t, before)
            th.record(t, TaskHistory.DELETED, req.user)
    bid = b.id
    return {'deleted': len(tasks), 'batch': bid}


def tasks_restore(gate, a):
    from tasks import history as th
    from tasks.models import Task, TaskHistory
    req = _req(gate)
    tasks = list(Task.objects.deleted().filter(id__in=a.get('ids') or []))
    with journal.Batch(gate.organization, req.user, 'tasks_restore', f'{len(tasks)} تسک') as b:
        for t in tasks:
            before = journal.snap(t)
            t.deleted_at, t.deleted_by = None, None
            t.save()
            journal.note_update(t, before)
            th.record(t, TaskHistory.RESTORED, req.user)
    bid = b.id
    return {'restored': len(tasks), 'batch': bid}


def task_comment(gate, a):
    from mcpgate.panel.ctx import call_view
    from tasks.api import task_comments
    text = str(a.get('text') or '').strip()
    body = text if '<' in text else ''.join(f'<p>{p}</p>' for p in text.split('\n') if p.strip())
    st, d = call_view(gate, task_comments, 'POST', {'body': body}, int(a['id']))
    if st >= 400:
        raise ToolError(d.get('detail') or f'خطا {st}')
    return {'ok': True, 'comment': d.get('id')}


def task_review(gate, a):
    from mcpgate.panel.ctx import call_view
    from tasks import api
    from tasks.models import Task
    t = Task.all_objects.filter(pk=a.get('id')).first()
    if not t:
        raise ToolError('تسک پیدا نشد')
    res = {'approved': 'approved', 'needs_fix': 'needs_fix', 'تایید': 'approved', 'اصلاح': 'needs_fix'}.get(a.get('result'))
    if not res:
        raise ToolError('result باید approved یا needs_fix باشد')
    before = journal.snap(t)
    with journal.Batch(gate.organization, _req(gate).user, 'task_review', f'#{t.id} {res}'):
        st, d = call_view(gate, api.task_review, 'PATCH', {'review_status': res, 'review_note': a.get('note') or ''}, t.id)
        if st >= 400:
            raise ToolError(d.get('detail') or f'خطا {st}')
        t.refresh_from_db()
        journal.note_update(t, before)
    return {'ok': True, 'status': t.status, 'review': t.review_status}


# ───────────── پروژه ─────────────
PROJECT_FIELDS = {'name': 'name', 'domain': 'domain', 'status': 'status', 'color': 'color', 'types': 'project_types',
                  'amount': 'amount', 'track_keyword_rank': 'track_keyword_rank', 'content_hourly_rate': 'content_hourly_rate',
                  'content_word_rate': 'content_word_rate', 'contract_start': 'contract_start', 'priority': 'priority'}


def projects_query(gate, a):
    from django.db.models import Count
    from projects.models import Project
    qs = Project.objects.filter(personal_owner__isnull=True)
    if a.get('status'):
        qs = qs.filter(status=a['status'])
    if a.get('q'):
        qs = qs.filter(Q(name__icontains=a['q']) | Q(domain__icontains=a['q']))
    qs = qs.annotate(open=Count('tasks', filter=Q(tasks__deleted_at__isnull=True) & ~Q(tasks__status__in=['done', 'pending'])),
                     done=Count('tasks', filter=Q(tasks__deleted_at__isnull=True, tasks__status='done')))
    rows = [[p.id, p.name, p.domain or None, p.status, p.open, p.done] for p in qs.order_by('name')[:int(a.get('limit') or 100)]]
    return table(['id', 'name', 'domain', 'status', 'open_tasks', 'done_tasks'], rows)


def project_get(gate, a):
    from projects.models import Project
    R = Resolver()
    p = Project.objects.filter(pk=R.get('project', a.get('project'))).first()
    out = {'id': p.id, 'name': p.name, 'domain': p.domain, 'status': p.status, 'types': p.project_types or None,
           'amount': int(p.amount) if p.amount else None, 'contract_start': jd(p.contract_start),
           'members': [c.full_name for c in p.members.all()] if hasattr(p, 'members') else None}
    return {k: v for k, v in out.items() if v not in (None, '', [])}


def project_save(gate, a):
    from projects.models import Project
    R = Resolver()
    req = _req(gate)
    f = a.get('fields') or {}
    pid = R.get('project', a['project']) if a.get('project') else None
    p = Project.objects.get(pk=pid) if pid else Project()
    if not pid and not f.get('name'):
        raise ToolError('برای پروژهٔ جدید name لازم است')
    before = journal.snap(p) if pid else None
    for k, v in f.items():
        attr = PROJECT_FIELDS.get(k)
        if not attr:
            raise ToolError(f'فیلدِ «{k}» نامعتبر. مجاز: {", ".join(PROJECT_FIELDS)}')
        if attr == 'contract_start':
            v = pdate(v)
        if attr == 'domain' and v:
            v = re.sub(r'^https?://(www\.)?', '', str(v)).strip('/')
        setattr(p, attr, v)
    if a.get('dry_run'):
        return {'dry_run': True, 'project': p.name}
    with journal.Batch(gate.organization, req.user, 'project_save', p.name) as b:
        if not pid:
            p.created_by = req.user
        p.save()
        journal.note_update(p, before) if pid else journal.note_create(p)
    bid = b.id
    return {'id': p.id, 'name': p.name, 'batch': bid}
