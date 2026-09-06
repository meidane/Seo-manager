"""بک‌فیلِ کلیدِ خالیِ TaskTypeField.

فیلدهایی که در migration 0027 ساخته شدند `key=''` گرفتند، چون `save()`ِ سفارشیِ مدل
(که `key='f<id>'` می‌گذارد) در migration اجرا نمی‌شود. فیلدِ بی‌کلید یعنی همهٔ فیلدهای
بی‌کلیدِ یک نوع روی کلیدِ '' برخورد می‌کنند (انکر/لینکِ رپورتاژ روی هم می‌نوشتند).
این migration هر فیلدِ بی‌کلید را `f<id>` می‌کند (idempotent).
"""
from django.db import migrations


def backfill(apps, schema_editor):
    TaskTypeField = apps.get_model('tasks', 'TaskTypeField')
    for f in TaskTypeField.objects.filter(key=''):
        f.key = f'f{f.pk}'
        f.save(update_fields=['key'])


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0027_reportage_fields_simplify'),
    ]
    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
