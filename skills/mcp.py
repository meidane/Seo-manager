"""MCPِ اسکیل‌ها — کانکتورِ جدا: `/mcp/<token>/skills/` (همان توکنِ `/settings/mcp/`).

ایندکس:
- TOOLS / BASE_INSTRUCTIONS / instructions(org)
- skills_start      ← تشخیصِ پروژه/نوع از هر سرنخ (text/site/task/project) + متنِ کاملِ اسکیل‌های لازم (`text.detect/select`)
- skills_list / skill_get / skill_save / skill_delete / skill_history / skill_restore
- skill_file_get / skill_file_save / skill_file_delete  ← ضمیمه‌ها (کد/عکسِ نمونه)
- کمکی‌های مشترک با وب: file_row, save_file_bytes, restore_version
نوشتن‌ها داخلِ `journal.Batch` → در لاگِ MCP و قابلِ بازگردانی. فعلاً بدونِ محدودیتِ نقش (خواستِ کاربر).
"""
import base64
import binascii

from django.core.files.base import ContentFile
from django.utils import timezone

from mcpgate.panel.ctx import Resolver, ToolError, fake_request, jd, table

from .models import Skill, SkillFile, SkillVersion
from .text import detect, live, select

S = lambda t, d='', **x: {'type': t, **({'description': d} if d else {}), **x}  # noqa: E731
ANY = {}
MAX_FILE = 10 * 1024 * 1024
TEXT_INLINE = 40000


def obj(props, req=()):
    return {'type': 'object', 'properties': props, 'required': list(req)}


TOOLS = [
    {'name': 'skills_start', 'description': 'قبل از هر کار (به‌خصوص تولیدِ محتوا): سرنخ بده (text = خودِ درخواست، site، project، task، type) '
     '→ پروژه و نوع خودکار تشخیص داده می‌شود و متنِ کاملِ اسکیل‌های لازم (اجباری + همیشه + مرتبط) برمی‌گردد؛ بقیه فقط عنوان.',
     'inputSchema': obj({'text': S('string', 'درخواستِ کاربر یا عنوانِ کار'), 'project': ANY, 'site': S('string', 'کلیدِ سایت در کانکتورِ سایت‌ها'),
                         'task': S('integer'), 'type': S('string', 'نوعِ تسک، مثلاً «انتشار» یا «رپورتاژ»')})},
    {'name': 'skills_list', 'description': 'فهرستِ اسکیل‌ها (بدونِ متن). فیلتر: scope (must|general|project)، project، category، q.',
     'inputSchema': obj({'scope': S('string'), 'project': ANY, 'category': S('string'), 'q': S('string'), 'inactive': S('boolean')})},
    {'name': 'skill_get', 'description': 'متنِ کاملِ یک یا چند اسکیل (ids یا title) + فهرستِ فایل‌هایش.',
     'inputSchema': obj({'ids': S('array'), 'title': S('string')})},
    {'name': 'skill_save', 'description': 'ساخت/ویرایشِ اسکیل (با id = ویرایش). فیلدها: scope, project, title, summary, body, append (افزودن به ته متن), '
     'apply (always|auto|manual), category, tags («مقاله, بلاگ»), task_types ([نامِ نوع])، order, active, note.',
     'inputSchema': obj({'items': S('array', '[{id?, scope, project, title, summary, body | append, apply, category, tags, task_types, note}]')}, ['items'])},
    {'name': 'skill_delete', 'description': 'حذفِ اسکیل (قابلِ بازگردانی با undo).', 'inputSchema': obj({'ids': S('array')}, ['ids'])},
    {'name': 'skill_history', 'description': 'نسخه‌های قبلیِ یک اسکیل.', 'inputSchema': obj({'id': S('integer')}, ['id'])},
    {'name': 'skill_restore', 'description': 'برگرداندنِ اسکیل به یک نسخهٔ قبلی.',
     'inputSchema': obj({'id': S('integer'), 'version': S('integer')}, ['id', 'version'])},
    {'name': 'skill_file_get', 'description': 'محتوای فایلِ ضمیمه: متن/کد کامل، عکس به‌صورتِ تصویر، بقیه لینک.',
     'inputSchema': obj({'id': S('integer')}, ['id'])},
    {'name': 'skill_file_save', 'description': 'افزودنِ فایل به اسکیل: text (کد/متن) یا base64 یا url. name با پسوند.',
     'inputSchema': obj({'skill': S('integer'), 'name': S('string'), 'text': S('string'), 'base64': S('string'), 'url': S('string'),
                         'note': S('string')}, ['skill', 'name'])},
    {'name': 'skill_file_delete', 'description': 'حذفِ فایلِ ضمیمه (قابلِ بازگردانی).', 'inputSchema': obj({'ids': S('array')}, ['ids'])},
    {'name': 'undo', 'description': 'بازگردانیِ یک دستهٔ تغییر (batch از خروجیِ نوشتن‌ها).',
     'inputSchema': obj({'batch': S('integer'), 'force': S('boolean')}, ['batch'])},
]

BASE_INSTRUCTIONS = (   # ثابت — هرگز با داده عوض نشود (ChatGPT فقط موقعِ وصل‌شدن می‌خواند؛ محتوای تازه از جوابِ ابزار)
    'اسکیل‌های سازمان (دانش و قواعدِ کار، به‌خصوص تولیدِ محتوا). سطح‌ها: «اجباری» (همیشه)، «عمومی»، «پروژه». '
    'قبل از هر کاری، اول ابزارِ skills_start را با text = متنِ درخواستِ کاربر (و site/project اگر معلوم است) صدا بزن و هر چه در load '
    'برگشت (از جمله قواعدِ اجباری) را کامل رعایت کن؛ متنِ اسکیل‌ها فقط از همین جواب بیاید چون همیشه تازه است. پروژه خودکار تشخیص داده می‌شود. '
    'اسکیل‌های load را کامل و دقیق رعایت کن؛ از available فقط اگر لازم شد skill_get بگیر. فایل‌های نمونه با skill_file_get. '
    'اگر کاربر نکتهٔ ماندگاری گفت، با skill_save (append) به اسکیلِ مناسب اضافه کن و به کاربر بگو.'
)


def instructions(org):
    """ثابت (org برای سازگاری) — اسکیل‌ها عمداً اینجا نیستند تا تغییرشان بدونِ رفرشِ کانکتور برسد."""
    return BASE_INSTRUCTIONS


def _scope(v):
    v = str(v or '').strip().lower()
    alias = {'must': 'must', 'must_use': 'must', 'اجباری': 'must', 'general': 'general', 'عمومی': 'general',
             'project': 'project', 'پروژه': 'project'}
    if v not in alias:
        raise ToolError('scope باید must|general|project باشد')
    return alias[v]


def _apply(v):
    v = str(v or '').strip().lower()
    alias = {'always': 'always', 'همیشه': 'always', 'auto': 'auto', 'خودکار': 'auto', 'manual': 'manual', 'دستی': 'manual'}
    if v not in alias:
        raise ToolError('apply باید always|auto|manual باشد')
    return alias[v]


def file_row(f, base=''):
    return [f.id, f.name, f.kind, f.size, f.note or None, base.rstrip('/') + f.public_path() if base else f.public_path()]


def _files(s, base):
    fs = [f for f in s.files.all() if not f.deleted_at]
    return table(['id', 'name', 'kind', 'bytes', 'note', 'url'], [file_row(f, base) for f in fs]) if fs else None


def skills_start(gate, a):
    org, base = gate.organization, getattr(gate, '_base', '')
    d = detect(org, project=a.get('project'), site=a.get('site'), task=a.get('task'), type=a.get('type'), text=a.get('text') or '')
    load, avail = select(org, d['project'], d['type'], d['text'])
    r = Resolver()
    out = {'detected': {'project': r.name('project', d['project']) if d['project'] else None, 'project_id': d['project'],
                        'type': r.name('type', d['type']) if d['type'] else None, 'task': d['task'], 'by': d['how'] or None}}
    if not d['project']:
        out['detected']['hint'] = 'پروژه تشخیص داده نشد — اگر کار برای سایتِ خاصی است، project یا site بده تا اسکیل‌های همان پروژه هم بیاید.'
    out['load'] = [{'id': s.id, 'title': s.title, 'why': why, 'body': s.body, **({'files': _files(s, base)} if _files(s, base) else {})}
                   for s, why in load]
    # دادهٔ سرچ کنسولِ صفحه (لینکِ داخلِ درخواست یا صفحهٔ تسک) — برای بازنویسی/آپدیتِ همان صفحه
    try:
        from gsc.analysis import briefs_for
        from tasks.models import Task
        t = Task.all_objects.filter(pk=d['task']).select_related('type_def').prefetch_related('type_def__fields').first() if d['task'] else None
        gsc = briefs_for(org, d['text'], t)
        if gsc:
            out['search_console'] = gsc
    except Exception:  # noqa: BLE001 — نبودِ داده نباید اسکیل‌ها را خراب کند
        pass
    if avail:
        out['available'] = table(['id', 'title', 'summary', 'scope'], [[s.id, s.title, s.summary or None, s.scope] for s, _ in avail[:40]])
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
    if a.get('category'):
        qs = qs.filter(category__icontains=a['category'])
    if a.get('q'):
        q = str(a['q'])
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(body__icontains=q) | Q(tags__icontains=q))
    rank = {Skill.MUST: 0, Skill.GENERAL: 1, Skill.PROJECT: 2}
    rows = sorted(qs[:300], key=lambda s: (rank[s.scope], s.project.name if s.project_id else '', s.order, s.id))
    return table(['id', 'scope', 'project', 'title', 'summary', 'apply', 'category', 'tags', 'updated'],
                 [[s.id, s.scope, s.project.name if s.project_id else None, s.title, s.summary or None, s.apply,
                   s.category or None, s.tags or None, jd(s.updated_at)] for s in rows])


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
    base = getattr(gate, '_base', '')
    return [{'id': s.id, 'scope': s.scope, 'project': s.project.name if s.project_id else None, 'title': s.title,
             'summary': s.summary, 'apply': s.apply, 'tags': s.tags or None, 'body': s.body, 'updated': jd(s.updated_at),
             **({'files': _files(s, base)} if _files(s, base) else {})} for s in out]


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
            for f in ('title', 'summary', 'category', 'tags'):
                if f in it:
                    setattr(s, f, str(it[f] or '').strip()[:{'summary': 300, 'tags': 400, 'category': 60}.get(f, 200)])
            if 'apply' in it:
                s.apply = _apply(it['apply'])
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
            if 'task_types' in it:
                tt = it['task_types'] or []
                s.task_types.set([r.get('type', t) for t in (tt if isinstance(tt, list) else [tt]) if t])
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


# ───────────── فایل‌ها ─────────────
def _clean_name(name):
    import os
    return os.path.basename(str(name or '')).strip().replace('/', '-').replace('\\', '-')[:200]


def save_file_bytes(skill, name, data, user, note=''):
    """منبعِ واحدِ ذخیرهٔ ضمیمه (وب و MCP). هم‌نامِ فعال در همان اسکیل → محتوایش جایگزین می‌شود (لینک ثابت می‌ماند)."""
    name = _clean_name(name)
    if not name:
        raise ToolError('نامِ فایل لازم است')
    if len(data) > MAX_FILE:
        raise ToolError(f'حداکثر حجم {MAX_FILE // (1024 * 1024)} مگابایت است')
    f = SkillFile.all_objects.filter(skill=skill, name=name, deleted_at__isnull=True).first() or \
        SkillFile(skill=skill, name=name, organization=skill.organization)
    f.file.save(name, ContentFile(data), save=False)
    f.size, f.uploaded_by = len(data), user
    if note:
        f.note = note[:300]
    f.save()
    return f


def _file(gate, pk):
    f = SkillFile.all_objects.filter(organization=gate.organization, pk=pk, deleted_at__isnull=True).select_related('skill').first()
    if not f:
        raise ToolError(f'فایلِ #{pk} پیدا نشد')
    return f


def skill_file_get(gate, a):
    f = _file(gate, int(a['id']))
    url = getattr(gate, '_base', '').rstrip('/') + f.public_path()
    with f.file.open('rb') as fh:
        data = fh.read()
    if f.kind == 'image' and len(data) <= 4 * 1024 * 1024:
        import mimetypes
        return {'_mcp': {'content': [{'type': 'text', 'text': f'{f.name} ({f.note or "عکسِ نمونه"}) — {url}'},
                                     {'type': 'image', 'data': base64.b64encode(data).decode(),
                                      'mimeType': mimetypes.guess_type(f.name)[0] or 'image/png'}]}}
    if f.kind == 'text':
        txt = data.decode('utf-8', errors='replace')
        return {'id': f.id, 'name': f.name, 'note': f.note or None, 'url': url,
                'text': txt[:TEXT_INLINE] + ('… [بریده شد]' if len(txt) > TEXT_INLINE else '')}
    return {'id': f.id, 'name': f.name, 'note': f.note or None, 'bytes': f.size, 'url': url}


def skill_file_save(gate, a):
    from mcpgate import journal
    s = _get(gate, int(a['skill']))
    if a.get('text') is not None:
        data = str(a['text']).encode('utf-8')
    elif a.get('base64'):
        try:
            data = base64.b64decode(str(a['base64']).split(',')[-1])
        except (binascii.Error, ValueError) as e:
            raise ToolError('base64 نامعتبر است') from e
    elif a.get('url'):
        import requests
        resp = requests.get(a['url'], timeout=40)
        resp.raise_for_status()
        data = resp.content
    else:
        raise ToolError('text یا base64 یا url لازم است')
    with _batch(gate, 'skill_file_save', f'«{a["name"]}» → {s.title}') as b:
        existed = SkillFile.all_objects.filter(skill=s, name=_clean_name(a['name']), deleted_at__isnull=True).exists()
        f = save_file_bytes(s, a['name'], data, fake_request(gate).user, a.get('note') or '')
        if not existed:
            journal.note_create(f)
    return {'batch': b.id, 'file': file_row(f, getattr(gate, '_base', '')), 'replaced': existed}


def skill_file_delete(gate, a):
    from mcpgate import journal
    ids = a.get('ids') or []
    with _batch(gate, 'skill_file_delete', f'حذفِ {len(ids)} فایل') as b:
        for i in ids[:50]:
            f = _file(gate, int(i))
            before = journal.snap(f)
            f.deleted_at = timezone.now()
            f.save()
            journal.note_update(f, before)
    return {'batch': b.id, 'deleted': len(ids)}


def undo(gate, a):
    from mcpgate.panel.registry import undo as panel_undo
    return panel_undo(gate, a)


HANDLERS = {'skills_start': skills_start, 'skills_list': skills_list, 'skill_get': skill_get, 'skill_save': skill_save,
            'skill_delete': skill_delete, 'skill_history': skill_history, 'skill_restore': skill_restore,
            'skill_file_get': skill_file_get, 'skill_file_save': skill_file_save, 'skill_file_delete': skill_file_delete,
            'undo': undo}


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
