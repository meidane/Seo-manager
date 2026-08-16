"""سیگنالِ اتصالِ کلماتِ کلیدیِ تسک به ردیابیِ رتبه.

هر بار تسکی ذخیره می‌شود که (۱) پروژه‌اش `track_keyword_rank` دارد، (۲) نوعِ سفارشی‌اش
هم فیلدِ «لینکِ صفحهٔ همین تسک» (`is_page_link`) پر دارد هم فیلدِ «کلمهٔ کلیدیِ
ردیابی‌شونده» (`is_keyword_source` + `track_keyword_rank`) پر دارد — کلماتش را با همان
لینک در `TrackedKeyword` ثبت/به‌روز می‌کند (idempotent، `get_or_create`؛ خودِ
افزونهٔ مرورگر بعداً رتبه‌اش را با `rank_ingest` پر می‌کند). منطق را جای دیگر تکرار نکن.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='tasks.Task')
def sync_tracked_keywords(sender, instance, **kwargs):
    task = instance
    if not task.project_id or not task.type_def_id or not isinstance(task.custom, dict):
        return
    project = task.project
    if not project.track_keyword_rank:
        return
    fields = list(task.type_def.fields.all())
    page_field = next((f for f in fields if f.is_page_link), None)
    if not page_field:
        return
    page_url = (task.custom.get(page_field.key) or '').strip()
    if not page_url:
        return

    from .models import TrackedKeyword

    for f in fields:
        if not (f.kind == f.TAGS and f.is_keyword_source and f.track_keyword_rank):
            continue
        for kw in task.custom.get(f.key) or []:
            kw = (kw or '').strip()
            if not kw:
                continue
            TrackedKeyword.all_objects.get_or_create(
                project=project, page_url=page_url, keyword=kw,
                defaults={'is_manual': False})
