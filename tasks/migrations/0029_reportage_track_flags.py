"""رپورتاژ: انکر و لینک چندخطی + فلگِ اتصال به ردیابیِ رتبه.

انکر → `is_keyword_source` (بدونِ track_keyword_rank)، لینک → `is_link_source`، هر دو
`textarea` (چندخطی). `seo/signals` این دو را خط‌به‌خط جفت و در `TrackedKeyword` ثبت می‌کند
تا فعالیتِ رپورتاژ در تبِ «کلمات کلیدی»ِ پروژه دیده شود. idempotent.
"""
from django.db import migrations


def flag(apps, schema_editor):
    TaskTypeDef = apps.get_model('tasks', 'TaskTypeDef')
    TaskTypeField = apps.get_model('tasks', 'TaskTypeField')
    for td in TaskTypeDef.objects.filter(name='رپورتاژ'):
        for f in td.fields.all():
            if f.label == 'انکر':
                f.kind = 'textarea'
                f.is_keyword_source = True
                f.placeholder = f.placeholder or 'هر انکر در یک خط'
                if not f.key:
                    f.key = f'f{f.pk}'
                f.save()
            elif f.label == 'لینک':
                f.kind = 'textarea'
                f.is_link_source = True
                f.placeholder = f.placeholder or 'هر لینک در یک خط'
                if not f.key:
                    f.key = f'f{f.pk}'
                f.save()


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0028_backfill_field_keys'),
    ]
    operations = [
        migrations.RunPython(flag, migrations.RunPython.noop),
    ]
