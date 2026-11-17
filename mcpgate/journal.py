"""ژورنالِ تغییراتِ MCP — منبعِ واحدِ «چه چیزی، کِی، با کدام دسته عوض شد» + بازگردانی.

- `Batch(org, user, tool, summary)` = context manager؛ داخلش `current_batch()` دستهٔ جاری است
  (`tasks.history.record` از همین می‌فهمد تغییر از MCP است و برچسب می‌زند).
- قبل از تغییر `before = snap(obj)`، بعد از ذخیره `note_update(obj, before)`؛ برای ساخت `note_create(obj)`.
  فقط فیلدهای تغییرکرده ذخیره می‌شوند (کم‌حجم).
- `undo(batch, user, force=False)`: به ترتیبِ معکوس — ساخته‌شده‌ها حذف (نرم اگر `deleted_at` دارد)،
  ویرایش‌شده‌ها به مقدارِ قبل، حذف‌شده‌ها بازیابی. اگر رکورد بعداً دستی عوض شده باشد (مقدارِ فعلی ≠
  `after`) آن رکورد رد می‌شود (مگر `force`) تا کارِ دستیِ بعدی از بین نرود.
"""
import contextvars
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from django.apps import apps
from django.db import transaction
from django.utils import timezone

_cur = contextvars.ContextVar('mcp_batch', default=None)

# فیلدهایی که در مقایسه/بازگردانی نادیده گرفته می‌شوند (خودکار/پرنوسان)
IGNORE = {'id', 'created_at', 'updated_at', 'timer_heartbeat', 'timer_started_at', 'spent_minutes', 'organization_id'}


def current_batch():
    return _cur.get()


def _js(v):
    if isinstance(v, (datetime, date, time)):
        return v.isoformat()
    if isinstance(v, (Decimal, uuid.UUID)):
        return str(v)
    if hasattr(v, 'name') and hasattr(v, 'storage'):   # FieldFile
        return v.name or ''
    return v


def snap(obj):
    """{attname: مقدارِ JSON‌پذیر} برای فیلدهای عادیِ مدل (بدونِ M2M)."""
    return {f.attname: _js(getattr(obj, f.attname)) for f in obj._meta.concrete_fields if f.attname not in IGNORE}


def _label(obj):
    return str(getattr(obj, 'title', None) or getattr(obj, 'name', None) or obj)[:200]


def _key(obj):
    return f'{obj._meta.app_label}.{obj._meta.object_name}'


class Batch:
    def __init__(self, org, user, tool, summary=''):
        self.org, self.user, self.tool, self.summary = org, user, tool, summary
        self.obj, self.token = None, None

    def __enter__(self):
        from .models import MCPBatch
        # همه‌یا‌هیچ: اگر ابزار وسطِ کار خطا داد، هیچ تغییری (حتی نیمه‌کاره) نمی‌ماند
        self.atomic = transaction.atomic()
        self.atomic.__enter__()
        self.obj = MCPBatch.objects.create(organization=self.org, user=self.user, tool=self.tool, summary=self.summary[:300])
        self.token = _cur.set(self.obj)
        return self

    def __exit__(self, exc_type, exc, tb):
        _cur.reset(self.token)
        if exc_type is None and not self.obj.changes.exists():
            self.obj.delete()      # دستهٔ بدونِ تغییر (پیش‌نمایش) لاگ نمی‌شود
        if exc_type is not None or not self.obj.pk:
            self.obj = None
        self.atomic.__exit__(exc_type, exc, tb)
        return False

    @property
    def id(self):
        return self.obj.pk if self.obj else None


def _add(op, obj, before=None, after=None):
    from .models import MCPChange
    b = current_batch()
    if not b:
        return
    MCPChange.objects.create(batch=b, model=_key(obj), object_id=obj.pk, label=_label(obj), op=op, before=before, after=after)


def _count(op):
    b = current_batch()
    if b is not None:
        # شمارش روی شیءِ Batchِ پایتونی نیست؛ مستقیم روی رکورد جمع می‌زنیم
        c = dict(b.counts or {})
        c[op] = c.get(op, 0) + 1
        b.counts = c
        b.save(update_fields=['counts'])


def note_create(obj):
    _add('create', obj, after=snap(obj))
    _count('create')


def note_update(obj, before):
    now = snap(obj)
    changed = {k: v for k, v in now.items() if before.get(k) != v}
    if not changed:
        return False
    op = 'delete' if ('deleted_at' in changed and now.get('deleted_at')) else 'update'
    _add(op, obj, before={k: before.get(k) for k in changed}, after=changed)
    _count(op)
    return True


def note_hard_delete(obj):
    """حذفِ واقعی (مثلاً ردیفِ گزارش) — کلِ رکورد ذخیره می‌شود تا بازسازی ممکن باشد."""
    _add('purge', obj, before={**snap(obj), 'id': obj.pk})
    _count('delete')


# ───────────── بازگردانی ─────────────
def _set(obj, data):
    fields = {f.attname: f for f in obj._meta.concrete_fields}
    for k, v in data.items():
        f = fields.get(k)
        if f is not None:
            setattr(obj, k, None if v is None else f.to_python(v))


def _same(obj, data):
    cur = snap(obj)
    return all(cur.get(k) == v for k, v in data.items() if k not in IGNORE)


def _hsnap(obj):
    if _key(obj) == 'tasks.Task':
        from tasks import history as th
        return th.snapshot(obj)
    return None


def _history(obj, action, user, hbefore=None):
    if _key(obj) == 'tasks.Task':
        from tasks import history as th
        th.record(obj, action, user, th.diff(obj, hbefore) if hbefore else None)


def undo(batch, user, force=False):
    """بازگردانیِ یک دسته. خروجی: {'undone': n, 'skipped': [(label, دلیل)]}."""
    from tasks.models import TaskHistory
    if batch.undone_at:
        return {'undone': 0, 'skipped': [], 'note': 'این دسته قبلاً بازگردانی شده'}
    done, skipped = 0, []
    with Batch(batch.organization, user, 'undo', f'بازگردانیِ دستهٔ #{batch.pk}'):
        for ch in batch.changes.filter(undone=False).order_by('-id'):
            Model = apps.get_model(ch.model)
            mgr = getattr(Model, 'all_objects', Model._default_manager)
            obj = mgr.filter(pk=ch.object_id).first()
            reason = ''
            if ch.op == 'purge':
                if obj:
                    reason = 'رکورد از قبل وجود دارد'
                else:
                    data = dict(ch.before)
                    new = Model(pk=data.pop('id'))
                    _set(new, data)
                    new.save()
                    note_create(new)
            elif not obj:
                reason = 'رکورد دیگر وجود ندارد'
            elif not force and not _same(obj, ch.after or {}):
                reason = 'بعد از MCP دستی تغییر کرده (برای بازگردانیِ اجباری force)'
            else:
                before, hbefore = snap(obj), _hsnap(obj)
                if ch.op == 'create':
                    if hasattr(obj, 'deleted_at'):
                        obj.deleted_at = timezone.now()
                        if hasattr(obj, 'deleted_by_id'):
                            obj.deleted_by_id = getattr(user, 'pk', None)
                        obj.save()
                        note_update(obj, before)
                        _history(obj, TaskHistory.DELETED, user)
                    else:
                        note_hard_delete(obj)
                        obj.delete()
                else:   # update / delete(نرم) → مقادیرِ قبلی
                    _set(obj, ch.before or {})
                    obj.save()
                    note_update(obj, before)
                    _history(obj, TaskHistory.RESTORED if ch.op == 'delete' else TaskHistory.UPDATED, user, hbefore)
            if reason:
                ch.undo_skip = reason[:200]
                ch.save(update_fields=['undo_skip'])
                skipped.append([ch.label, reason])
            else:
                ch.undone = True
                ch.undo_skip = ''
                ch.save(update_fields=['undone', 'undo_skip'])
                done += 1
    if not batch.changes.filter(undone=False).exists():
        batch.undone_at = timezone.now()
        batch.undone_by = user if getattr(user, 'pk', None) else None
    batch.undo_note = (f'{done} بازگردانده شد' + (f'، {len(skipped)} رد شد' if skipped else ''))[:300]
    batch.save(update_fields=['undone_at', 'undone_by', 'undo_note'])
    return {'undone': done, 'skipped': skipped}
