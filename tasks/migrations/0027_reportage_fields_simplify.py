"""رپورتاژ ساده‌شد: فقط «انکر» (متن) + «لینک» (متن بلند/چندخطی).

فیلدهای قدیمیِ رپورتاژ (کلمات کلیدی، تعداد کلمه، مترادف و LSI، عنوان سئو، لینک صفحه،
کلمه کلیدی هدف، لینک هدف) حذف می‌شوند. idempotent است — فقط نوعِ نامِ «رپورتاژ» را
دست می‌زند و فیلدهای موردنظر را تضمین می‌کند. دادهٔ `Task.custom` دست‌نخورده می‌ماند
(فقط تعریفِ فیلد حذف می‌شود؛ مقادیرِ قدیمی در JSON می‌مانند ولی دیگر نمایش داده نمی‌شوند).
"""
from django.db import migrations

REPORTAGE = 'رپورتاژ'
KEEP = {'انکر', 'لینک'}


def simplify(apps, schema_editor):
    TaskTypeDef = apps.get_model('tasks', 'TaskTypeDef')
    TaskTypeField = apps.get_model('tasks', 'TaskTypeField')
    for td in TaskTypeDef.objects.filter(name=REPORTAGE):
        # فیلدهای غیرِمجاز را حذف کن
        td.fields.exclude(label__in=KEEP).delete()
        existing = set(td.fields.values_list('label', flat=True))
        order = td.fields.count()
        if 'انکر' not in existing:
            f = TaskTypeField.objects.create(type_def=td, label='انکر', kind='text', order=order)
            f.key = f'f{f.pk}'; f.save(update_fields=['key'])   # save()ِ سفارشی در migration اجرا نمی‌شود
            order += 1
        if 'لینک' not in existing:
            f = TaskTypeField.objects.create(
                type_def=td, label='لینک', kind='textarea',
                placeholder='هر لینک در یک خط', order=order)
            f.key = f'f{f.pk}'; f.save(update_fields=['key'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0026_task_timer_heartbeat'),
    ]
    operations = [
        migrations.RunPython(simplify, noop),
    ]
