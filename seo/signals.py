"""سیگنالِ اتصالِ کلماتِ کلیدیِ تسک به ردیابیِ رتبه.

هر بار تسکی ذخیره می‌شود که (۱) پروژه‌اش `track_keyword_rank` دارد، (۲) نوعِ سفارشی‌اش
هم فیلدِ «لینکِ صفحهٔ همین تسک» (`is_page_link`) پر دارد هم فیلدِ «کلمهٔ کلیدیِ
ردیابی‌شونده» (`is_keyword_source` + `track_keyword_rank`) پر دارد — کلماتش را با همان
لینک در `TrackedKeyword` ثبت/به‌روز می‌کند (idempotent، `get_or_create`؛ خودِ
افزونهٔ مرورگر بعداً رتبه‌اش را با `rank_ingest` پر می‌کند). منطق را جای دیگر تکرار نکن.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


def _lines(value):
    """مقدارِ یک فیلد را به لیستِ خطوطِ ناخالی تبدیل می‌کند (رشتهٔ چندخطی یا لیست)."""
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [ln.strip() for ln in (value or '').split('\n') if ln.strip()]


@receiver(post_save, sender='tasks.Task')
def sync_tracked_keywords(sender, instance, **kwargs):
    task = instance
    if not task.project_id or not task.type_def_id or not isinstance(task.custom, dict):
        return
    project = task.project
    if not project.track_keyword_rank:
        return
    fields = list(task.type_def.fields.all())

    from .models import TrackedKeyword

    # ── الگوی ۱ (انتشار/آپدیت): یک صفحهٔ همین تسک (is_page_link) + کلماتِ tagsِ ردیابی‌شونده ──
    page_field = next((f for f in fields if f.is_page_link), None)
    page_url = (task.custom.get(page_field.key) or '').strip() if page_field else ''
    if page_url:
        for f in fields:
            if not (f.kind == f.TAGS and f.is_keyword_source and f.track_keyword_rank):
                continue
            for kw in _lines(task.custom.get(f.key)):
                TrackedKeyword.all_objects.get_or_create(
                    project=project, page_url=page_url, keyword=kw,
                    defaults={'is_manual': False})

    # ── الگوی ۲ (رپورتاژ): لینکِ چندخطی (is_link_source) + انکرِ چندخطی (is_keyword_source) ──
    #   هر خطِ لینک با همان خطِ انکر جفت می‌شود → TrackedKeyword(page_url=لینک, keyword=انکر)
    #   تا فعالیتِ رپورتاژ در تبِ «کلمات کلیدی»ِ پروژه هم دیده/ردیابی شود.
    link_field = next((f for f in fields if f.is_link_source), None)
    anchor_field = next((f for f in fields
                         if f.is_keyword_source and not f.track_keyword_rank and f is not link_field), None)
    if link_field and anchor_field:
        links = _lines(task.custom.get(link_field.key))
        anchors = _lines(task.custom.get(anchor_field.key))
        for i, link in enumerate(links):
            kw = anchors[i] if i < len(anchors) else ''
            if link and kw:
                TrackedKeyword.all_objects.get_or_create(
                    project=project, page_url=link, keyword=kw,
                    defaults={'is_manual': False})
