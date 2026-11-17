"""ورود از اکسل/CSV — فایل روی سرور خوانده می‌شود (نه از چتِ هوش مصنوعی) تا توکن نسوزد.

۱) `import_inspect(file)`: فایل از بخشِ «فایل‌ها»ی پنل (نام یا id) یا URL → سلول‌های پرِ هر شیت، فشرده (هر ردیف یک
   آرایه، سلولِ بلند کوتاه‌شده). اکسلِ نامرتب (ستون‌های متفاوت برای هر پروژه، تیترِ وسطِ جدول، ردیفِ خالی) را خودِ
   هوش مصنوعی می‌فهمد و ردیف‌های تمیز می‌سازد.
۲) `import_tasks(rows, defaults, dedupe, on_duplicate, dry_run)`: همان ردیف‌های `tasks_save` + تشخیصِ تکراری
   (لینکِ صفحه/رپورتاژ در همان پروژه، یا عنوان+تاریخ) هم با دیتابیس هم داخلِ همین فایل. پیش‌فرض dry_run=true.
"""
import csv
import io
import re

from mcpgate.panel import tasks as T
from mcpgate.panel.ctx import Resolver, ToolError, pdate


def _open(ref):
    """(نامِ فایل، بایت‌ها) از فایل‌های پنل (نام/بخشی از نام/id) یا URL."""
    from filebox.models import SharedFile
    ref = str(ref or '').strip()
    if not ref:
        raise ToolError('file لازم است (نام یا id فایل در بخشِ «فایل‌ها»ی پنل)')
    if re.match(r'^https?://', ref):
        m = re.search(r'/f/[^/]+/(.+)$', ref)
        if not m:
            import requests
            r = requests.get(ref, timeout=60)
            r.raise_for_status()
            return ref.rsplit('/', 1)[-1], r.content
        from urllib.parse import unquote
        ref = unquote(m.group(1)).rsplit('/', 1)[-1]
    qs = SharedFile.objects.all()
    f = (qs.filter(pk=int(ref)).first() if ref.isdigit() else None) or qs.filter(name=ref).first() \
        or qs.filter(name__icontains=ref).order_by('-updated_at').first()
    if not f:
        names = list(qs.filter(name__iregex=r'\.(xlsx|xlsm|csv)$').values_list('name', flat=True)[:10])
        raise ToolError(f'فایلِ «{ref}» در بخشِ فایل‌ها نیست. اکسل‌های موجود: {"، ".join(names) or "—"}')
    with f.file.open('rb') as fh:
        return f.name, fh.read()


def _cell(v, maxlen):
    if v is None:
        return None
    if hasattr(v, 'isoformat'):
        from core.jalali import format_jalali
        try:
            return f'{v.date().isoformat() if hasattr(v, "date") else v.isoformat()} ({format_jalali(v.date() if hasattr(v, "date") else v)})'
        except Exception:  # noqa: BLE001
            return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = re.sub(r'\s+', ' ', str(v)).strip()
    if not s:
        return None
    return s if len(s) <= maxlen else s[:maxlen] + '…'


def read_sheets(name, data, max_rows=400, maxlen=120, sheet=None, offset=0):
    out = []
    if name.lower().endswith('.csv'):
        text = data.decode('utf-8-sig', errors='replace')
        rows = [[_cell(c, maxlen) for c in r] for r in csv.reader(io.StringIO(text))]
        out.append(('csv', rows))
    else:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        for ws in wb.worksheets:
            if sheet and ws.title != sheet:
                continue
            rows = [[_cell(c, maxlen) for c in r] for r in ws.iter_rows(values_only=True)]
            out.append((ws.title, rows))
    result = []
    for title, rows in out:
        # ردیف‌های کاملاً خالی حذف، ستون‌های خالیِ انتهایی بریده؛ شمارهٔ ردیفِ اصلی نگه داشته می‌شود
        clean = []
        for i, r in enumerate(rows, 1):
            while r and r[-1] is None:
                r = r[:-1]
            if any(c is not None for c in r):
                clean.append([i] + r)
        total = len(clean)
        result.append({'sheet': title, 'rows_total': total, 'note': 'ستونِ اول = شمارهٔ ردیف در فایل',
                       'rows': clean[offset:offset + max_rows],
                       'next_offset': offset + max_rows if offset + max_rows < total else None})
    return result


def import_inspect(gate, a):
    name, data = _open(a.get('file'))
    sheets = read_sheets(name, data, max_rows=min(int(a.get('max_rows') or 400), 1000),
                         sheet=a.get('sheet'), offset=int(a.get('offset') or 0))
    return {'file': name, 'sheets': sheets,
            'next': 'ردیف‌ها را به قالبِ import_tasks تبدیل کن (اول dry_run)؛ ستون‌های نامرتبِ هر پروژه را خودت نگاشت کن.'}


def _dupe_index(R, rows, td, defaults):
    """{project_id: {'links': {url: task_id}, 'td': {(title, date): task_id}}} برای پروژه‌های این فایل."""
    from tasks.models import Task
    pids = set()
    for r in rows:
        p = r.get('project') or defaults.get('project')
        pid = R.get('project', p, required=False) if p else None
        if pid:
            pids.add(pid)
    idx = {}
    if not pids:
        return idx
    pl = T._page_link_field(td) if td else None
    qs = Task.objects.filter(project_id__in=pids).only('id', 'project_id', 'title', 'done_date', 'planned_date', 'custom',
                                                      'published_url', 'type_def_id')
    for t in qs:
        d = idx.setdefault(t.project_id, {'links': {}, 'td': {}})
        for u in [(t.custom or {}).get(pl.key) if pl else None, t.published_url]:
            if u:
                d['links'][T._norm_url(u)] = t.id
        d['td'][(_nt(t.title), t.done_date or t.planned_date)] = t.id
    return idx


def _nt(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip().lower()


def import_tasks(gate, a):
    from tasks.models import TaskTypeDef
    rows = a.get('rows') or []
    if not rows:
        raise ToolError('rows خالی است')
    if len(rows) > 500:
        raise ToolError('حداکثر ۵۰۰ ردیف در هر فراخوانی — چند بخش کن')
    defaults = dict(a.get('defaults') or {})
    defaults.setdefault('status', 'done')
    R = Resolver()
    td = None
    tname = defaults.get('type')
    if tname:
        td = TaskTypeDef.objects.prefetch_related('fields').get(pk=R.get('type', tname))
    dedupe = a.get('dedupe') or ('link' if T._page_link_field(td) else 'title_date')
    on_dup = a.get('on_duplicate') or 'skip'
    idx = _dupe_index(R, rows, td, defaults) if dedupe != 'none' else {}
    seen = set()
    items, pre = [], []   # pre: نتیجه‌های ردیف‌هایی که به ذخیره نمی‌رسند
    for i, r in enumerate(rows):
        r = dict(r)
        try:
            pid = R.get('project', r.get('project') or defaults.get('project'))
        except ToolError as e:
            pre.append((i, 'error', str(e)))
            continue
        link = T._norm_url(r.get('link')) if r.get('link') else ''
        dkey = None
        try:
            dt = pdate(r.get('done') or r.get('planned'))
        except ToolError as e:
            pre.append((i, 'error', str(e)))
            continue
        if dedupe == 'link' and link:
            dkey = ('l', pid, link)
            hit = idx.get(pid, {}).get('links', {}).get(link)
        elif dedupe != 'none':
            dkey = ('t', pid, _nt(r.get('title')), dt)
            hit = idx.get(pid, {}).get('td', {}).get((_nt(r.get('title')), dt))
        else:
            hit = None
        if dkey and dkey in seen:
            pre.append((i, 'duplicate_in_file', 'تکراری داخلِ همین فایل'))
            continue
        if dkey:
            seen.add(dkey)
        if hit:
            if on_dup == 'update':
                r['id'] = hit
                r.pop('type', None)
            else:
                pre.append((i, 'duplicate', f'از قبل هست: تسکِ #{hit}'))
                continue
        items.append((i, r))
    dry = a.get('dry_run', True)
    results = {}
    from mcpgate import journal
    req, R2 = T._req(gate), Resolver()
    with journal.Batch(gate.organization, req.user, 'import_tasks', f'{len(rows)} ردیف از {a.get("source") or "اکسل"}') as b:
        for i, r in items:
            try:
                results[i] = T._save_one(gate, req, R2, r, defaults, dry)
            except ToolError as e:
                results[i] = ('error', None, str(e))
    bid = b.id
    keys = sorted(results)
    out = T._summary([results[k] for k in keys], dry, None if dry else bid, rows_idx=keys)
    if pre:
        c = out['counts']
        for _, op, _m in pre:
            c[op] = c.get(op, 0) + 1
        out['skipped'] = {'cols': ['row', 'reason', 'detail'], 'rows': [[i, op, m] for i, op, m in pre][:40]}
    out['dedupe'] = dedupe
    return out
