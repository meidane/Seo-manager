"""ارقامِ فارسیِ ذخیره‌شده در فیلدهای متنیِ تراکنش‌ها را به لاتین تبدیل می‌کند.

برای داده‌ی قدیمی که موقعِ ایمپورت با ارقامِ فارسی ذخیره شده (شرح سند/توضیحات).
idempotent است؛ اجرای دوباره بی‌اثر است.

    python manage.py normalize_digits          # فقط گزارش (dry-run)
    python manage.py normalize_digits --apply   # اعمالِ واقعی
"""
from django.core.management.base import BaseCommand

from core.jalali import to_en_digits
from finance.models import Transaction

_FA = set('۰۱۲۳۴۵۶۷۸۹')
_FIELDS = ('description', 'note', 'user_note')


class Command(BaseCommand):
    help = 'تبدیلِ ارقامِ فارسیِ فیلدهای متنیِ تراکنش‌ها به لاتین (شرح/توضیحات).'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='اعمالِ واقعیِ تغییرات (بدونِ آن فقط شمارش می‌شود).')

    def handle(self, *args, **opts):
        apply = opts['apply']
        changed = 0
        # all_objects: بدونِ فیلترِ سازمان (همه‌ی سازمان‌ها)
        for t in Transaction.all_objects.all().iterator():
            dirty = False
            for f in _FIELDS:
                v = getattr(t, f, '') or ''
                if any(c in _FA for c in v):
                    if apply:
                        setattr(t, f, to_en_digits(v))
                    dirty = True
            if dirty:
                changed += 1
                if apply:
                    t.save(update_fields=list(_FIELDS))
        verb = 'به‌روزرسانی شد' if apply else 'نیازمندِ تبدیل است (برای اعمال: --apply)'
        self.stdout.write(self.style.SUCCESS(f'{changed} تراکنش {verb}.'))
