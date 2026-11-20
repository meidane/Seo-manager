from django.core.management.base import BaseCommand

from gsc.sync import run_all


class Command(BaseCommand):
    help = 'همگام‌سازیِ شبانهٔ سرچ کنسول برای همهٔ سازمان‌ها (روی cron بگذار، مثلاً هر شب ساعت ۴)'

    def handle(self, *args, **opts):
        run_all(log=lambda m: self.stdout.write(m))
