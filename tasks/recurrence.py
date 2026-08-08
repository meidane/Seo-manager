"""تولید تنبلِ تسک‌های تکرارشونده.

اصل: همیشه یک تسکِ واقعیِ فعال + یک پیش‌نما (placeholder) جلوتر. با done شدنِ تسکِ
فعلی، پیش‌نما واقعی می‌شود و یک پیش‌نمای تازه ساخته می‌شود.
"""
from .models import Task

# فیلدهایی که موقعِ ساختِ رخدادِ بعدی از تسکِ مبدأ کپی می‌شوند
_COPY = [
    'project_id', 'assignee_id', 'task_type', 'type_def_id', 'update_type',
    'title', 'description', 'planned_time', 'priority', 'estimate_minutes',
    'word_count', 'keywords', 'lsi_keywords', 'seo_title', 'current_rank',
    'published_url', 'source_url', 'media_name', 'media_cost', 'anchor_text',
    'target_url', 'link_type', 'link_count', 'custom', 'organization_id',
]


def _clone(src, planned_date, placeholder):
    data = {f: getattr(src, f) for f in _COPY}
    t = Task(**data)
    t.planned_date = planned_date
    t.status = Task.TODO
    t.done_date = None
    t.recurrence_id = src.recurrence_id
    t.is_placeholder = placeholder
    t.save()
    return t


def create_placeholder(src):
    """یک پیش‌نمای بعدی برای سریِ src بساز (با رعایتِ سقفِ count/end_date)."""
    rule = src.recurrence
    if not rule or not rule.active:
        return None
    total = Task.all_objects.filter(recurrence=rule).count()
    if rule.count and total >= rule.count:
        return None
    nd = rule.next_date(src.planned_date)
    if rule.end_date and nd > rule.end_date:
        return None
    return _clone(src, nd, placeholder=True)


def start_series(task):
    """پس از ساختِ تسکِ اولِ یک سری، اولین پیش‌نما را بساز."""
    return create_placeholder(task)


def advance(task):
    """تسکِ واقعیِ done → پیش‌نمای بعدی را واقعی کن و پیش‌نمای تازه بساز."""
    rule = task.recurrence
    if not rule or task.is_placeholder or not rule.active:
        return
    ph = (Task.all_objects.filter(recurrence=rule, is_placeholder=True)
          .order_by('planned_date').first())
    if ph:
        ph.is_placeholder = False
        ph.save(update_fields=['is_placeholder'])
        create_placeholder(ph)
    else:
        create_placeholder(task)
