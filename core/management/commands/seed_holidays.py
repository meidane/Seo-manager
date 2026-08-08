"""دستور seed تعطیلات از فایل‌های JSON سالانه.

استفاده:
    python manage.py seed_holidays 1405              # یک سال
    python manage.py seed_holidays 1405 1406 1407     # چند سال
    python manage.py seed_holidays 1405-1408          # بازه
    python manage.py seed_holidays                    # همه‌ی فایل‌های موجود

فایل داده در `core/data/holidays_<year>.json` قرار می‌گیرد و هر ورودی شامل
تاریخ شمسی، عنوان، نوع و پرچم تعطیل است. تاریخ به میلادی تبدیل و ذخیره می‌شود.

نکته: تعطیلات قمری (مذهبی) بر پایه‌ی تقویم رصدیِ ایران‌اند و ممکن است در سال‌های
آینده ±۱ روز با تقویم رسمیِ نهایی تفاوت کنند؛ فایل JSON قابل ویرایش است.
"""
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.jalali import parse_jalali
from core.models import Holiday

DATA_DIR = Path(__file__).resolve().parent.parent.parent / 'data'


class Command(BaseCommand):
    help = 'بارگذاری تعطیلات یک یا چند سال شمسی از فایل‌های JSON'

    def add_arguments(self, parser):
        parser.add_argument(
            'years', nargs='*',
            help='سال‌های شمسی؛ مثلاً 1405 یا 1405 1406 یا بازه‌ی 1405-1408. '
                 'خالی = همه‌ی فایل‌های موجود.')

    def _resolve_years(self, args):
        """آرگومان‌ها را به فهرست سال تبدیل کن (تک، چند، بازه، یا همه)."""
        if not args:
            years = sorted(int(p.stem.split('_')[1]) for p in DATA_DIR.glob('holidays_*.json'))
            if not years:
                raise CommandError(f'هیچ فایل تعطیلاتی در {DATA_DIR} نیست.')
            return years
        years = []
        for a in args:
            m = re.fullmatch(r'(\d{4})-(\d{4})', a)
            if m:
                lo, hi = int(m.group(1)), int(m.group(2))
                years.extend(range(lo, hi + 1))
            else:
                years.append(int(a))
        return years

    def handle(self, *args, **options):
        years = self._resolve_years(options['years'])
        grand_c, grand_u = 0, 0
        for year in years:
            path = DATA_DIR / f'holidays_{year}.json'
            if not path.exists():
                self.stderr.write(self.style.WARNING(f'رد شد (فایل نیست): {path}'))
                continue

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
                created += was_created
                updated += not was_created
            grand_c += created
            grand_u += updated
            self.stdout.write(
                f'  سال {year}: {created} افزوده، {updated} به‌روزرسانی.')

        self.stdout.write(self.style.SUCCESS(
            f'مجموع: {grand_c} تعطیلی افزوده و {grand_u} به‌روزرسانی شد.'))
