"""تعریفِ ابزارهای MCPِ پنل (`/mcp/<token>/panel/`) + اجرا. توضیحِ ابزارها عمداً کوتاه است (هر گفتگو کلِ این
فهرست را می‌خواند)؛ جزئیاتِ قالب در `INSTRUCTIONS` یک‌جا آمده."""
from mcpgate.panel import finance as F
from mcpgate.panel import importer as I
from mcpgate.panel import reports as RP
from mcpgate.panel import tasks as T
from mcpgate.panel.ctx import MONTHS, Resolver, ToolError, jd, table

S = lambda t, d='', **x: {'type': t, **({'description': d} if d else {}), **x}  # noqa: E731
ANY = {}
ARR = lambda d='': S('array', d)  # noqa: E731


def obj(props, req=()):
    return {'type': 'object', 'properties': props, 'required': list(req)}


FILTER = S('object', 'project, assignee, type, status, from/to (برنامه), done_from/done_to, report_month («1403-07»|none), q, ids, overdue, no_date')

TOOLS = [
    {'name': 'panel_info', 'description': 'اولِ هر گفتگو یک بار: انواعِ تسک و فیلدهایشان، افراد، پروژه‌ها، بابت‌ها، ماه‌های گزارش.', 'inputSchema': obj({})},
    {'name': 'find', 'description': 'جستجوی سریع در پروژه/فرد/تسک/گزارش با نام، دامنه یا بخشی از عنوان.',
     'inputSchema': obj({'q': S('string'), 'kind': S('string', 'project|colleague|task|report (اختیاری)')}, ['q'])},
    {'name': 'tasks_query', 'description': 'فهرستِ تسک‌ها (جدولِ فشرده). fields اضافه: description, estimate, spent, deadline, review, words, fields, link.',
     'inputSchema': obj({'project': ANY, 'assignee': ANY, 'type': ANY, 'status': ANY, 'from': S('string'),
                         'to': S('string'), 'done_from': S('string'), 'done_to': S('string'), 'report_month': S('string'),
                         'q': S('string'), 'ids': ARR(), 'overdue': S('boolean'), 'no_date': S('boolean'), 'deleted': S('boolean'),
                         'fields': ARR(), 'order': S('string', 'planned|-planned|done|-done|id'), 'limit': S('integer'),
                         'offset': S('integer'), 'count_only': S('boolean')})},
    {'name': 'task_get', 'description': 'جزئیاتِ یک تسک. include: history, comments.',
     'inputSchema': obj({'id': S('integer'), 'include': ARR()}, ['id'])},
    {'name': 'tasks_save', 'description': 'ساخت/ویرایشِ گروهیِ تسک (با id = ویرایش). اول dry_run=true.',
     'inputSchema': obj({'items': ARR('ردیف‌ها (قالب در راهنما)'), 'defaults': S('object', 'مقادیرِ پیش‌فرضِ همهٔ ردیف‌ها'),
                         'dry_run': S('boolean')}, ['items'])},
    {'name': 'tasks_update_where', 'description': 'تغییرِ گروهی با فیلتر (مثلاً همهٔ تسک‌های X را done کن). پیش‌فرض dry_run.',
     'inputSchema': obj({'filter': FILTER, 'set': S('object', 'همان فیلدهای ردیفِ tasks_save'), 'dry_run': S('boolean')}, ['filter', 'set'])},
    {'name': 'tasks_delete', 'description': 'حذفِ نرم (سطلِ زباله) با ids یا filter. پیش‌فرض dry_run.',
     'inputSchema': obj({'ids': ARR(), 'filter': FILTER, 'dry_run': S('boolean')})},
    {'name': 'tasks_restore', 'description': 'بازیابیِ تسک‌های حذف‌شده.', 'inputSchema': obj({'ids': ARR()}, ['ids'])},
    {'name': 'task_comment', 'description': 'افزودنِ «گزارشِ کار» به تسک.', 'inputSchema': obj({'id': S('integer'), 'text': S('string')}, ['id', 'text'])},
    {'name': 'task_review', 'description': 'بازبینی: approved یا needs_fix (+ note).',
     'inputSchema': obj({'id': S('integer'), 'result': S('string'), 'note': S('string')}, ['id', 'result'])},
    {'name': 'projects_query', 'description': 'فهرستِ پروژه‌ها + تعدادِ تسکِ باز/انجام‌شده.',
     'inputSchema': obj({'q': S('string'), 'status': S('string'), 'limit': S('integer')})},
    {'name': 'project_get', 'description': 'مشخصاتِ پروژه.', 'inputSchema': obj({'project': ANY}, ['project'])},
    {'name': 'project_save', 'description': 'ساخت/ویرایشِ پروژه. fields: name, domain, status, color, types, amount, contract_start, ...',
     'inputSchema': obj({'project': ANY, 'fields': S('object'), 'dry_run': S('boolean')}, ['fields'])},
    {'name': 'import_inspect', 'description': 'خواندنِ اکسل/CSV از بخشِ «فایل‌ها»ی پنل (نام یا id یا لینک) روی سرور → ردیف‌های فشرده.',
     'inputSchema': obj({'file': S('string'), 'sheet': S('string'), 'offset': S('integer'), 'max_rows': S('integer')}, ['file'])},
    {'name': 'import_tasks', 'description': 'ورودِ ردیف‌های تمیزشده به تسک + تشخیصِ تکراری (لینکِ صفحه/رپورتاژ یا عنوان+تاریخ). پیش‌فرض dry_run.',
     'inputSchema': obj({'rows': ARR(), 'defaults': S('object', 'مثلاً {"type":"رپورتاژ","status":"done"}'),
                         'dedupe': S('string', 'link|title_date|none'), 'on_duplicate': S('string', 'skip|update'),
                         'source': S('string', 'نامِ فایل (برای لاگ)'), 'dry_run': S('boolean')}, ['rows'])},
    {'name': 'stats', 'description': 'آمارِ سمتِ سرور. metric: count|hours|estimate|words|cost|review، by: assignee|project|type|status|month|week|none.',
     'inputSchema': obj({'metric': S('string'), 'by': S('string'), 'filter': FILTER,
                         'period': S('string', 'this_month|last_month|last_30|this_year'),
                         'month_by': S('string', 'done (پیش‌فرض) | report'), 'limit': S('integer')})},
    {'name': 'project_health', 'description': 'خلاصهٔ وضعیتِ یک پروژه (باز/عقب‌افتاده/کارِ ماه‌ها/ساعت/مانده/آخرین گزارش/کلمات).',
     'inputSchema': obj({'project': ANY, 'months': S('integer')}, ['project'])},
    {'name': 'reports_query', 'description': 'فهرستِ گزارش‌های مشتری.', 'inputSchema': obj({'project': ANY, 'status': S('string'), 'limit': S('integer')})},
    {'name': 'report_get', 'description': 'جزئیاتِ گزارش. include: items, keywords, sections.',
     'inputSchema': obj({'id': S('integer'), 'include': ARR()}, ['id'])},
    {'name': 'report_create', 'description': 'ساختِ گزارش برای ماه («1403-07») یا from/to؛ add_tasks: done (پیش‌فرض) | all | none | [ids].',
     'inputSchema': obj({'project': ANY, 'month': S('string'), 'from': S('string'), 'to': S('string'), 'title': S('string'),
                         'description': S('string'), 'add_tasks': ANY, 'dry_run': S('boolean')}, ['project'])},
    {'name': 'report_update', 'description': 'ویرایشِ گزارش: title, description, status (draft|final = لینکِ عمومی), add_tasks, remove_items, keywords[{id?,keyword,position,change,note,delete}], sections[{id?,title,description,delete}].',
     'inputSchema': obj({'id': S('integer'), 'title': S('string'), 'description': S('string'), 'status': S('string'),
                         'is_public': S('boolean'), 'add_tasks': ARR(), 'remove_items': ARR(), 'keywords': ARR(),
                         'sections': ARR()}, ['id'])},
    {'name': 'tx_queue', 'description': 'صفِ تراکنش‌های بی‌تخصیص برای پیشنهاد (فشرده + نمونه‌های هم‌شکلِ قبلی). بعدش tx_suggest.',
     'inputSchema': obj({'limit': S('integer'), 'offset': S('integer'), 'bank': ANY, 'include_suggested': S('boolean')})},
    {'name': 'tx_suggest', 'description': 'ثبتِ پیشنهادِ پروژه/بابت/توضیح برای تراکنش‌ها (فقط پیشنهاد؛ تأیید با کاربر در پنل).',
     'inputSchema': obj({'items': ARR('[{id, project, categories:[...], note, why}]')}, ['items'])},
    {'name': 'tx_query', 'description': 'جستجوی تراکنش‌ها (جدولِ فشرده).',
     'inputSchema': obj({'q': S('string'), 'project': ANY, 'category': ANY, 'bank': ANY, 'from': S('string'), 'to': S('string'),
                         'kind': S('string', 'in|out'), 'unassigned': S('boolean'), 'min': S('integer'), 'max': S('integer'),
                         'limit': S('integer'), 'offset': S('integer')})},
    {'name': 'finance_stats', 'description': 'جمعِ واریز/برداشت بر اساسِ category|project|month|bank (+ فاکتور در category).',
     'inputSchema': obj({'by': S('string'), 'from': S('string'), 'to': S('string'), 'project': ANY})},
    {'name': 'actions_list', 'description': 'لاگِ تغییراتِ MCP (دسته‌ها، قابلِ بازگردانی).', 'inputSchema': obj({'limit': S('integer')})},
    {'name': 'undo', 'description': 'بازگردانیِ یک دسته (batch). force=true حتی اگر بعداً دستی تغییر کرده.',
     'inputSchema': obj({'batch': S('integer'), 'force': S('boolean')}, ['batch'])},
]

INSTRUCTIONS = (
    'پنلِ مدیریتِ پروژه‌های سئو (فارسی، تاریخ شمسی). شروع: panel_info. پروژه/فرد/نوع را با نام یا دامنه بده — سرور خودش پیدا می‌کند. '
    'ردیفِ تسک: {id?, title, project, assignee, type, status(todo|doing|pending|done), planned, done, deadline (شمسی 1403/07/15 یا ISO), '
    'estimate («1:30»), report_month («1403-07»|none), description, checklist, needs_review, link (لینکِ صفحه/رپورتاژ), fields {برچسبِ فیلدِ نوع: مقدار}}. '
    'نوشتن‌ها: اول dry_run=true، خلاصه را به کاربر بگو، بعد اجرا. هر نوشتن یک batch دارد و با undo برمی‌گردد. '
    'کارها را گروهی بفرست (items/rows تا ۵۰۰)، نه یکی‌یکی. برای آمار از stats/project_health استفاده کن، نه دریافتِ همهٔ ردیف‌ها. '
    'اکسل: کاربر فایل را در «فایل‌ها»ی پنل آپلود می‌کند → import_inspect → ردیف‌های تمیز → import_tasks(dry_run) → import_tasks. '
    'رپورتاژ: type=رپورتاژ، status=done، done=تاریخِ انتشار، link=لینکِ رپورتاژ، fields: {انکر, لینک (لینکِ هدف؛ چندتا با خطِ جدید), رسانه, هزینه}. '
    'تراکنش‌ها: فقط پیشنهاد (tx_queue → tx_suggest)؛ ثبتِ مستقیم نداریم.'
)


# ───────────── ابزارهای عمومی ─────────────
def panel_info(gate, a):
    from colleagues.models import Colleague
    from finance.models import Category
    from projects.models import Project
    from tasks.models import ReportPeriod, TaskTypeDef
    types = []
    for td in TaskTypeDef.objects.filter(is_active=True).prefetch_related('fields').order_by('order'):
        types.append([td.id, td.name, [f'{f.label}:{f.kind}' for f in td.fields.all()] or None])
    rp = [f'{p.year}-{p.month:02d}' for p in ReportPeriod.objects.order_by('-year', '-month')[:8]]
    return {
        'today': jd(__import__('datetime').date.today()),
        'types': table(['id', 'name', 'fields'], types),
        'projects': table(['id', 'name', 'domain'], [[p.id, p.name, p.domain or None] for p in
                                                       Project.objects.filter(personal_owner__isnull=True, status='active').order_by('name')]),
        'people': table(['id', 'name'], [[c.id, c.full_name] for c in Colleague.objects.filter(status='active')]),
        'categories': table(['id', 'name'], [[c.id, c.name] for c in Category.objects.all()]),
        'report_months': rp, 'months': MONTHS,
    }


def find(gate, a):
    from django.db.models import Q
    from colleagues.models import Colleague
    from projects.models import Project
    from reports.models import Report
    from tasks.models import Task
    q, kind, out = str(a.get('q') or '').strip(), a.get('kind'), {}
    if not q:
        raise ToolError('q لازم است')
    if kind in (None, 'project'):
        out['projects'] = [[p.id, p.name, p.domain or None] for p in
                           Project.objects.filter(Q(name__icontains=q) | Q(domain__icontains=q))[:10]]
    if kind in (None, 'colleague'):
        out['people'] = [[c.id, c.full_name] for c in Colleague.objects.filter(full_name__icontains=q)[:10]]
    if kind in (None, 'task'):
        out['tasks'] = [[t.id, t.title, t.project.name if t.project_id else None, t.status, jd(t.done_date or t.planned_date)]
                        for t in Task.objects.filter(title__icontains=q).select_related('project').order_by('-id')[:15]]
    if kind in (None, 'report'):
        out['reports'] = [[r.id, r.title, r.project.name] for r in Report.objects.filter(title__icontains=q).select_related('project')[:10]]
    if not any(out.values()):
        try:
            pid = Resolver().get('project', q)
            out['projects'] = [[pid, Resolver().name('project', pid), None]]
        except ToolError as e:
            return {'none': str(e)}
    return {k: v for k, v in out.items() if v}


def actions_list(gate, a):
    from mcpgate.models import MCPBatch
    rows = [[b.id, jd(b.created_at), b.created_at.strftime('%H:%M'), b.tool, b.summary, b.counts or None,
             bool(b.undone_at)] for b in MCPBatch.objects.filter(organization=gate.organization)[:int(a.get('limit') or 15)]]
    return table(['batch', 'date', 'time', 'tool', 'summary', 'counts', 'undone'], rows)


def undo(gate, a):
    from mcpgate import journal
    from mcpgate.models import MCPBatch
    from mcpgate.panel.ctx import fake_request
    b = MCPBatch.objects.filter(organization=gate.organization, pk=a.get('batch')).first()
    if not b:
        raise ToolError('دسته پیدا نشد')
    return journal.undo(b, fake_request(gate).user, force=bool(a.get('force')))


HANDLERS = {
    'panel_info': panel_info, 'find': find, 'actions_list': actions_list, 'undo': undo,
    'tasks_query': T.tasks_query, 'task_get': T.task_get, 'tasks_save': T.tasks_save,
    'tasks_update_where': T.tasks_update_where, 'tasks_delete': T.tasks_delete, 'tasks_restore': T.tasks_restore,
    'task_comment': T.task_comment, 'task_review': T.task_review,
    'projects_query': T.projects_query, 'project_get': T.project_get, 'project_save': T.project_save,
    'import_inspect': I.import_inspect, 'import_tasks': I.import_tasks,
    'stats': RP.stats, 'project_health': RP.project_health,
    'reports_query': RP.reports_query, 'report_get': RP.report_get, 'report_create': RP.report_create,
    'report_update': RP.report_update,
    'tx_queue': F.tx_queue, 'tx_suggest': F.tx_suggest, 'tx_query': F.tx_query, 'finance_stats': F.finance_stats,
}


def run(gate, name, args, log):
    fn = HANDLERS.get(name)
    if not fn:
        raise ToolError(f'ابزارِ ناشناخته: {name}')
    log['site'] = 'panel'
    from accounts.tenancy import clear_current_org, set_current_org
    set_current_org(gate.organization)
    try:
        return fn(gate, args or {})
    finally:
        clear_current_org()
