"""بوت‌استرپِ چندشرکتی: یک سازمانِ پیش‌فرض بساز، تیم‌های موجود را به آن وصل کن،
و برای هر کاربر یک عضویت ایجاد کن (سوپریوزر → مالک، بقیه → عضو).
این‌طور نصبِ فعلی بدون شکستن به مدلِ جدید مهاجرت می‌کند."""
from django.db import migrations


def forwards(apps, schema_editor):
    Organization = apps.get_model('accounts', 'Organization')
    Team = apps.get_model('accounts', 'Team')
    User = apps.get_model('accounts', 'User')
    Membership = apps.get_model('accounts', 'Membership')
    TeamMembership = apps.get_model('accounts', 'TeamMembership')

    if not User.objects.exists() and not Team.objects.exists():
        return  # نصب کاملاً خالی؛ نیازی به سازمان پیش‌فرض نیست

    org, _ = Organization.objects.get_or_create(
        slug='default', defaults={'name': 'سازمان پیش‌فرض'})

    Team.objects.filter(organization__isnull=True).update(organization=org)

    for u in User.objects.all():
        role = 'owner' if u.is_superuser else 'member'
        Membership.objects.get_or_create(
            user=u, organization=org, defaults={'role': role})
        if u.team_id:  # آینه‌ی فیلد قدیمیِ team در جدول جدید
            TeamMembership.objects.get_or_create(user=u, team_id=u.team_id)


def backwards(apps, schema_editor):
    Organization = apps.get_model('accounts', 'Organization')
    Organization.objects.filter(slug='default').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_organization_alter_team_options_team_parent_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
