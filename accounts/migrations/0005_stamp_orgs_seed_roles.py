"""دادهٔ چندشرکتی: نقش‌های پیش‌فرضِ هر سازمان را بساز و همه‌ی رکوردهای موجودِ
اپ‌ها را به «سازمان پیش‌فرض» نسبت بده (نصبِ تک‌شرکتیِ فعلی → یک tenant)."""
from django.db import migrations

from accounts.permissions import ROLE_CHOICES, ROLE_PERMS

# مدل‌های tenant که فیلد organization دارند: (app_label, ModelName)
TENANT_MODELS = [
    ('projects', 'Project'),
    ('colleagues', 'Colleague'),
    ('tasks', 'Task'),
    ('tasks', 'TaskTypeDef'),
    ('reports', 'Report'),
    ('finance', 'BankAccount'),
    ('finance', 'Category'),
    ('finance', 'Transaction'),
    ('finance', 'Payroll'),
]


def forwards(apps, schema_editor):
    Organization = apps.get_model('accounts', 'Organization')
    Role = apps.get_model('accounts', 'Role')

    org = Organization.objects.filter(slug='default').first() or Organization.objects.first()

    # نقش‌های پیش‌فرض برای همه‌ی سازمان‌ها
    for o in Organization.objects.all():
        for key, name in ROLE_CHOICES:
            Role.objects.get_or_create(
                organization=o, key=key,
                defaults={'name': name, 'perms': sorted(ROLE_PERMS.get(key, set())),
                          'is_builtin': True})

    if not org:
        return
    for app_label, model_name in TENANT_MODELS:
        Model = apps.get_model(app_label, model_name)
        Model.objects.filter(organization__isnull=True).update(organization=org)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_user_phone_role'),
        ('projects', '0002_alter_project_options_alter_project_managers_and_more'),
        ('colleagues', '0002_alter_colleague_options_alter_colleague_managers_and_more'),
        ('tasks', '0008_alter_task_options_alter_tasktypedef_options_and_more'),
        ('reports', '0002_alter_report_options_alter_report_managers_and_more'),
        ('finance', '0002_alter_bankaccount_options_alter_category_options_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
