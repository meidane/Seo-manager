"""کدِ عمومیِ کوتاه را برای گزارش‌های موجود پر می‌کند."""
from django.db import migrations


def backfill(apps, schema_editor):
    from reports.models import gen_public_code
    Report = apps.get_model('reports', 'Report')
    used = set(Report.objects.exclude(public_code__isnull=True)
               .values_list('public_code', flat=True))
    for r in Report.objects.filter(public_code__isnull=True):
        code = gen_public_code()
        while code in used:
            code = gen_public_code()
        used.add(code)
        r.public_code = code
        r.save(update_fields=['public_code'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [('reports', '0007_report_public_code')]
    operations = [migrations.RunPython(backfill, noop)]
