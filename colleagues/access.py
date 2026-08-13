"""دسترسیِ scoped به زیرمجموعه — مکملِ پرمیشنِ org-wide `manage_people`، برای اینکه
یک مدیر بدونِ دسترسیِ سازمانیِ کامل هم بتواند زیردست‌های خودش را مدیریت کند (نه فقط
مالک/مدیرِ کل). منبعِ واحدِ محاسبه‌ی زیرمجموعه‌ی مدیریتی — هم اینجا هم `tasks/queries.py`
(بازبینیِ تسک) از همین می‌خوانند."""
from .models import Colleague


def all_subordinate_ids(colleague, max_depth=20):
    """id‌ی همه‌ی زیرمجموعه‌ها در هر عمقی از زنجیره‌ی مدیریتی (نه فقط مستقیم) — یعنی
    زیردست، زیردستِ زیردست، و... . با BFS روی `Colleague.manager` (`related_name='reports'`)
    محاسبه می‌شود؛ `max_depth` صرفاً یک سقفِ دفاعی در برابرِ چرخه‌ی دادهٔ خراب است، نه یک
    محدودیتِ واقعیِ سازمانی (زنجیره‌های واقعی خیلی کوتاه‌ترند)."""
    if not colleague:
        return set()
    seen = {colleague.id}
    frontier = [colleague.id]
    for _ in range(max_depth):
        if not frontier:
            break
        nxt = list(Colleague.objects.filter(manager_id__in=frontier).exclude(id__in=seen)
                   .values_list('id', flat=True))
        if not nxt:
            break
        seen.update(nxt)
        frontier = nxt
    seen.discard(colleague.id)
    return seen


def is_manager_tier(request):
    """«سرپرست» است؟ یعنی زیرمجموعه‌ی مستقیم دارد یا پرمیشنِ سازمانیِ ناظر بر بقیه
    (`review`/`manage_people`/`view_all_projects`). همان معیاری که `tasks/queries.py:
    build_task_queryset` برای پیش‌فرضِ «فقط تسک‌های خودم» استفاده می‌کند."""
    m = getattr(request, 'membership', None)
    my_colleague = getattr(request.user, 'colleague', None)
    has_reports = bool(my_colleague and my_colleague.reports.exists())
    return has_reports or bool(m and (
        m.can('review') or m.can('manage_people') or m.can('view_all_projects')))
