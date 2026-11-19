"""MCPِ اسکیل‌ها — کانکتورِ جدا: `/mcp/<token>/skills/` (همان توکنِ `/settings/mcp/`).

کم‌مصرف: `skills_start` متنِ کاملِ «اجباری» + فقط عنوان/خلاصهٔ بقیه؛ متنِ کامل با `skill_get` (فقط وقتی لازم است).
نوشتن‌ها (`skill_save`/`skill_delete`/`skill_restore`) داخلِ `journal.Batch` → در لاگِ MCP و قابلِ بازگردانی.
هر ذخیره خودش یک `SkillVersion` (source=mcp) می‌سازد. فعلاً بدونِ محدودیتِ نقش (خواستِ کاربر).
"""
from django.utils import timezone

from mcpgate.panel.ctx import Resolver, ToolError, fake_request, jd, table

from .models import Skill, SkillVersion
from .text import for_project, live, must_use_text

S = lambda t, d='', **x: {'type': t, **({'description': d} if d else {}), **x}  # noqa: E731
ANY = {}


def obj(props, req=()):
    return {'type': 'object', 'properties': props, 'required': list(req)}


TOOLS = [
    {'name': 'skills_start', 'description': 'اولِ هر کار/گفتگو: متنِ کاملِ اسکیل‌های «اجباری» + فهرستِ عمومی‌ها و اسکیل‌های پروژه (عنوان+خلاصه). project = نام/دامنه/id.',
     'inputSchema': obj({'project': ANY})},
    {'name': 'skills_list', 'description': 'فهرستِ اسکیل‌ها (بدونِ متن). scope: must|general|project، project، q (جستجو در عنوان/خلاصه/متن).',
     'inputSchema': obj({'scope': S('string'), 'project': ANY, 'q': S('string'), 'inactive': S('boolean')})},
    {'name': 'skill_get', 'description': 'متنِ کاملِ یک یا چند اسکیل (ids یا title).',
     'inputSchema': obj({'ids': S('array'), 'title': S('string')})},
    {'name': 'skill_save', 'description': 'ساخت/ویرایشِ اسکیل (با id = ویرایش). فیلدها: scope, project, title, summary, body, append (افزودن به ته متن به‌جای جایگزینی), order, active, note (توضیحِ تغییر).',
     'inputSchema': obj({'items': S('array', '[{id?, scope, project, title, summary, body | append, order, active, note}]')}, ['items'])},
    {'name': 'skill_delete', 'description': 'حذفِ اسکیل (قابلِ بازگردانی با undo).', 'inputSchema': obj({'ids': S('array')}, ['ids'])},
    {'name': 'skill_history', 'description': 'نسخه‌های قبلیِ یک اسکیل.', 'inputSchema': obj({'id': S('integer')}, ['id'])},
    {'name': 'skill_restore', 'description': 'برگرداندنِ اسکیل به یک نسخهٔ قبلی.',
     'inputSchema': obj({'id': S('integer'), 'version': S('integer')}, ['id', 'version'])},
    {'name': 'undo', 'description': 'بازگردانیِ یک دستهٔ تغییر (batch از خروجیِ نوشتن‌ها).',
     'inputSchema': obj({'batch': S('integer'), 'force': S('boolean')}, ['batch'])},
]

BASE_INSTRUCTIONS = (
    'اسکیل‌های سازمان (دانش و قواعدِ کار). سه سطح: «اجباری» (همیشه رعایت شود)، «عمومی»، «پروژه». '
    'اولِ هر کار skills_start(project) را بزن؛ متنِ کاملِ اسکیلِ مرتبط را با skill_get بخوان و طبقِ آن کار کن. '
    'اگر کاربر نکتهٔ تازه‌ای گفت که باید ماندگار شود، با skill_save (append) به اسکیلِ مناسب اضافه کن و به کاربر بگو.'
)


def instructions(org):
    must = must_use_text(org)
    return BASE_INSTRUCTIONS + ('\n\n' + must if must else '')


def _row(s):
    return [s.id, s.scope, s.project.name if s.project_id else None, s.title, s.summary or None]


def _scope(v):
    v = str(v or '').strip().lower()
    alias = {'must': 'must', 'must_use': 'must', 'اجباری': 'must', 'general': 'general', 'عمومی': 'general',
             'project': 'project', 'پروژه': 'project'}
    if v not in alias:
        raise ToolError('scope باید must|general|project باشد')
    return alias[v]


def skills_start(gate, a):
    r = Resolver()
    pid = r.get('project', a.get('project'))
    rows = for_project(gate.organization, pid)
    must = [{'id': s.id, 'title': s.title, 'body': s.body} for s in rows if s.scope == Skill.MUST]
    out = {'must_use': must,
           'general': table(['id', 'title', 'summary'], [[s.id, s.title, s.summary or None] for s in rows if s.scope == Skill.GENERAL])}
    if pid:
        out['project'] = r.name('project', pid)
        out['project_skills'] = table(['id', 'title', 'summary'],
                                      [[s.id, s.title, s.summary or None] for s in rows if s.scope == Skill.PROJECT])
    else:
        out['hint'] = 'برای اسکیل‌های یک پروژه: skills_start(project)'
    return out


def skills_list(gate, a):
    from django.db.models import Q
    qs = Skill.all_objects.filter(organization=gate.organization, deleted_at__isnull=True).select_related('project')
    if not a.get('inactive'):
        qs = qs.filter(active=True)
    if a.get('scope'):
        qs = qs.filter(scope=_scope(a['scope']))
    if a.get('project'):
        qs = qs.filter(project_id=Resolver().get('project', a['project']))
    if a.get('q'):
        q = str(a['q'])
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(body__icontains=q))
    rank = {Skill.MUST: 0, Skill.GENERAL: 1, Skill.PROJECT: 2}
    rows = sorted(qs[:300], key=lambda s: (rank[s.scope], s.project.name if s.project_id else '', s.order, s.id))
    return table(['id', 'scope', 'project', 'title', 'summary', 'updated'], [_row(s) + [jd(s.updated_at)] for s in rows])


def _get(gate, pk):
    s = Skill.all_objects.filter(organization=gate.organization, pk=pk, deleted_at__isnull=True).select_related('project').first()
    if not s:
        raise ToolError(f'اسکیلِ #{pk} پیدا نشد')
    return s


def skill_get(gate, a):
    ids = a.get('ids') or []
    if not isinstance(ids, list):
        ids = [ids]
    out = [_get(gate, int(i)) for i in ids[:10]]
    if a.get('title'):
        t = str(a['title']).strip()
        base = live(gate.organization)
        s = base.filter(title=t).first() or base.filter(title__icontains=t).first()
        if not s:
            raise ToolError(f'اسکیلی با عنوانِ «{t}» نیست')
        out.append(s)
    if not out:
        raise ToolError('ids یا title لازم است')
    return [{'id': s.id, 'scope': s.scope, 'project': s.project.name if s.project_id else None, 'title': s.title,
             'summary': s.summary, 'body': s.body, 'updated': jd(s.updated_at)} for s in out]


def _batch(gate, tool, summary):
    from mcpgate import journal
    return journal.Batch(gate.organization, fake_request(gate).user, tool, summary)


def skill_save(gate, a):
    from mcpgate import journal
    items = a.get('items') or []
    if isinstance(items, dict):
        items = [items]
    if not items:
        raise ToolError('items خالی است')
    user, r, res = fake_request(gate).user, Resolver(), []
    with _batch(gate, 'skill_save', f'{len(items)} اسکیل') as b:
        for it in items[:50]:
            s = _get(gate, int(it['id'])) if it.get('id') else Skill(organization=gate.organization)
            before = journal.snap(s) if s.pk else None
            if 'scope' in it or not s.pk:
                s.scope = _scope(it.get('scope') or ('project' if it.get('project') else 'general'))
            if 'project' in it:
                s.project_id = r.get('project', it['project'], required=bool(it['project']))
            if s.scope == Skill.PROJECT and not s.project_id:
                raise ToolError(f'اسکیلِ پروژه‌ای «{it.get("title") or s.title}» پروژه لازم دارد')
            for f in ('title', 'summary'):
                if f in it:
                    setattr(s, f, str(it[f] or '').strip()[:300 if f == 'summary' else 200])
            if 'body' in it:
                s.body = str(it['body'] or '')
            if it.get('append'):
                s.body = (s.body.rstrip() + '\n\n' + str(it['append']).strip()).strip()
            for f in ('order', 'active'):
                if f in it:
                    setattr(s, f, int(it[f] or 0) if f == 'order' else bool(it[f]))
            if not s.title:
                raise ToolError('title لازم است')
            new = not s.pk
            s.save(actor=user, source='mcp', note=str(it.get('note') or ''))
            journal.note_create(s) if new else journal.note_update(s, before)
            res.append([s.id, 'create' if new else 'update', s.title])
    return {'batch': b.id, **table(['id', 'op', 'title'], res)}


def skill_delete(gate, a):
    from mcpgate import journal
    ids = a.get('ids') or []
    with _batch(gate, 'skill_delete', f'حذفِ {len(ids)} اسکیل') as b:
        for i in ids[:50]:
            s = _get(gate, int(i))
            before = journal.snap(s)
            s.deleted_at = timezone.now()
            s.save()
            journal.note_update(s, before)
    return {'batch': b.id, 'deleted': len(ids)}


def skill_history(gate, a):
    s = _get(gate, int(a['id']))
    return table(['version', 'date', 'time', 'by', 'source', 'title', 'chars', 'note'],
                 [[v.id, jd(v.created_at), timezone.localtime(v.created_at).strftime('%H:%M'),
                   (v.user.get_full_name() or v.user.username) if v.user_id else None, v.source, v.title, len(v.body), v.note or None]
                  for v in s.versions.select_related('user')[:30]])


def skill_restore(gate, a):
    from mcpgate import journal
    s = _get(gate, int(a['id']))
    v = SkillVersion.objects.filter(skill=s, pk=a['version']).first()
    if not v:
        raise ToolError('نسخه پیدا نشد')
    with _batch(gate, 'skill_restore', f'«{s.title}» ← نسخهٔ #{v.id}') as b:
        before = journal.snap(s)
        restore_version(s, v, fake_request(gate).user, source='mcp')
        journal.note_update(s, before)
    return {'batch': b.id, 'restored': v.id}


def restore_version(s, v, user, source='web'):
    s.title, s.summary, s.body, s.scope, s.project_id = v.title, v.summary, v.body, v.scope, v.project_id
    s.save(actor=user, source=source, note=f'بازگردانی به نسخهٔ #{v.id}')


def undo(gate, a):
    from mcpgate.panel.registry import undo as panel_undo
    return panel_undo(gate, a)


HANDLERS = {'skills_start': skills_start, 'skills_list': skills_list, 'skill_get': skill_get, 'skill_save': skill_save,
            'skill_delete': skill_delete, 'skill_history': skill_history, 'skill_restore': skill_restore, 'undo': undo}


def run(gate, name, args, log):
    fn = HANDLERS.get(name)
    if not fn:
        raise ToolError(f'ابزارِ ناشناخته: {name}')
    log['site'] = 'skills'
    from accounts.tenancy import clear_current_org, set_current_org
    set_current_org(gate.organization)
    try:
        return fn(gate, args or {})
    finally:
        clear_current_org()
