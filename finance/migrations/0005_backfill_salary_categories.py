"""برای همه‌ی همکارانِ موجود، بابتِ «حقوق <نام>» بساز و لینک کن (idempotent)."""
from django.db import migrations


def forwards(apps, schema_editor):
    Colleague = apps.get_model('colleagues', 'Colleague')
    Category = apps.get_model('finance', 'Category')
    for col in Colleague.objects.all():
        if not col.organization_id:
            continue
        name = f'حقوق {col.full_name}'.strip()
        if Category.objects.filter(colleague_id=col.id).exists():
            continue
        cat, _ = Category.objects.get_or_create(
            organization_id=col.organization_id, name=name,
            defaults={'is_salary': True, 'color': col.color or '#FBBF24', 'order': 100})
        changed = False
        if cat.colleague_id != col.id:
            cat.colleague_id = col.id
            changed = True
        if not cat.is_salary:
            cat.is_salary = True
            changed = True
        if changed:
            cat.save()


def backwards(apps, schema_editor):
    # لینک‌ها را باز کن؛ بابت‌ها را حذف نکن (ممکن است تراکنش به آن‌ها خورده باشد)
    Category = apps.get_model('finance', 'Category')
    Category.objects.filter(colleague__isnull=False).update(colleague=None)


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0004_category_colleague'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
