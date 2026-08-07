"""بابت‌های پیش‌فرض قابل‌گسترش."""
from django.core.management.base import BaseCommand

from finance.models import Category

DEFAULTS = [
    ('سئو', '#38BDF8', False), ('طراحی سایت', '#4183F2', False),
    ('فنی', '#A78BFA', False), ('تولید محتوا', '#F472B6', False),
    ('حقوق', '#FBBF24', True), ('هزینه‌های جاری', '#8FA0B8', False), ('سایر', '#5F6B80', False),
]


class Command(BaseCommand):
    help = 'ساخت بابت‌های پیش‌فرض'

    def handle(self, *args, **options):
        n = 0
        for i, (name, color, sal) in enumerate(DEFAULTS):
            _, c = Category.objects.get_or_create(name=name, defaults={'color': color, 'is_salary': sal, 'order': i})
            n += c
        self.stdout.write(self.style.SUCCESS(f'بابت‌ها آماده شد ({n} جدید).'))
