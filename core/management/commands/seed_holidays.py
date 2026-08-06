"""دستور seed تعطیلات از فایل JSON سالانه.

استفاده:  python manage.py seed_holidays 1405

فایل داده در `core/data/holidays_<year>.json` قرار می‌گیرد و هر ورودی شامل
تاریخ شمسی، عنوان، نوع و پرچم تعطیل است. تاریخ به میلادی تبدیل و ذخیره می‌شود.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.jalali import parse_jalali
from core.models import Holiday

DATA_DIR = Path(__file__).resolve().parent.parent.parent / 'data'


class Command(BaseCommand):
    help = 'بارگذاری تعطیلات یک سال شمسی از فایل JSON'

    def add_arguments(self, parser):
        parser.add_argument('year', type=int, help='سال شمسی، مثلاً 1405')

    def handle(self, *args, **options):
        year = options['year']
        path = DATA_DIR / f'holidays_{year}.json'
        if not path.exists():
            raise CommandError(f'فایل داده یافت نشد: {path}')

        entries = json.loads(path.read_text(encoding='utf-8'))
        created, updated = 0, 0

        for entry in entries:
            gdate = parse_jalali(entry['date'])
            _, was_created = Holiday.objects.update_or_create(
                date=gdate,
                defaults={
                    'title': entry['title'],
                    'kind': entry.get('kind', Holiday.OFFICIAL),
                    'is_off': entry.get('is_off', True),
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'تعطیلات سال {year}: {created} افزوده، {updated} به‌روزرسانی شد.'
            )
        )
