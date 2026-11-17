"""رپورتاژ: افزودنِ فیلدهای «رسانه»، «هزینه» و «لینک رپورتاژ» به نوعِ موجودِ «رپورتاژ» در هر سازمان
(برای ورودِ رپورتاژهای قدیمی از اکسل + گزارش/تحلیلِ هزینه). یک‌باره و ایمن: فیلدِ هم‌نامِ موجود دوباره ساخته نمی‌شود."""
from django.db import migrations

NEW = [
    {'label': 'رسانه', 'kind': 'text', 'width': 'half', 'placeholder': 'نامِ سایت/رسانهٔ منتشرکننده'},
    {'label': 'هزینه', 'kind': 'number', 'width': 'half', 'placeholder': 'ریال'},
    {'label': 'لینک رپورتاژ', 'kind': 'url', 'is_page_link': True, 'placeholder': 'آدرسِ رپورتاژِ منتشرشده'},
]


def forward(apps, schema_editor):
    TaskTypeDef = apps.get_model('tasks', 'TaskTypeDef')
    TaskTypeField = apps.get_model('tasks', 'TaskTypeField')
    for td in TaskTypeDef.objects.filter(name='رپورتاژ'):
        have = set(TaskTypeField.objects.filter(type_def=td).values_list('label', flat=True))
        order = (TaskTypeField.objects.filter(type_def=td).order_by('-order').values_list('order', flat=True).first() or 0)
        for spec in NEW:
            if spec['label'] in have:
                continue
            order += 1
            f = TaskTypeField.objects.create(type_def=td, order=order, **spec)
            f.key = f'f{f.pk}'
            f.save(update_fields=['key'])


class Migration(migrations.Migration):
    dependencies = [('seo', '0001_initial'), ('tasks', '0032_taskhistory_batch_id_taskhistory_source')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
