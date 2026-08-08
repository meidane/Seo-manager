"""بابت‌های پیش‌فرض قابل‌گسترش (per سازمان)."""
from django.core.management.base import BaseCommand

from accounts.models import Organization
from finance.models import Category

DEFAULTS = [
    ('سئو', '#38BDF8', False), ('طراحی سایت', '#4183F2', False),
    ('فنی', '#A78BFA', False), ('تولید محتوا', '#F472B6', False),
    ('حقوق', '#FBBF24', True), ('هزینه‌های جاری', '#8FA0B8', False), ('سایر', '#5F6B80', False),
]


class Command(BaseCommand):
    help = 'ساخت بابت‌های پیش‌فرض برای هر سازمان'

    def add_arguments(self, parser):
        parser.add_argument('--org', type=int, default=None, help='فقط این سازمان (id)')

    def handle(self, *args, **options):
        orgs = (Organization.objects.filter(id=options['org']) if options['org']
                else Organization.objects.all())
        n = 0
        for org in orgs:
            for i, (name, color, sal) in enumerate(DEFAULTS):
                _, c = Category.all_objects.get_or_create(
                    organization=org, name=name,
                    defaults={'color': color, 'is_salary': sal, 'order': i})
                n += c
        self.stdout.write(self.style.SUCCESS(f'بابت‌ها برای {orgs.count()} سازمان آماده شد ({n} جدید).'))
