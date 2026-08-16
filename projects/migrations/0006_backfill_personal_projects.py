"""برای هر همکارِ موجود یک پروژه‌ی «شخصی» بساز (idempotent)."""
from django.db import migrations


def forwards(apps, schema_editor):
    Colleague = apps.get_model('colleagues', 'Colleague')
    Project = apps.get_model('projects', 'Project')
    for col in Colleague.objects.all():
        if not col.organization_id:
            continue
        if Project.objects.filter(personal_owner_id=col.id).exists():
            continue
        p = Project.objects.create(
            organization_id=col.organization_id, name='شخصی',
            personal_owner_id=col.id, manager_id=col.id,
            color=col.color or '#8FA0B8', status='active')
        p.members.set([col])


def backwards(apps, schema_editor):
    Project = apps.get_model('projects', 'Project')
    Project.objects.filter(personal_owner__isnull=False).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0005_project_personal_owner'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
