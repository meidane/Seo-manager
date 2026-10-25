"""صفحهٔ «همگام‌سازیِ ChatGPT-WP» در تنظیمات — فقط نمایشِ وضعیت + راهنمای اتصال (ساده)."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from accounts.access import require_perm

from .models import SyncFile, SyncStore


class SyncPageView(LoginRequiredMixin, TemplateView):
    template_name = 'connector/sync.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = require_perm(self.request, 'manage_api_tokens')
        store = SyncStore.objects.filter(organization=org).first()
        data = store.get_data() if store else {}
        files = SyncFile.objects.filter(organization=org)
        ctx.update(
            page_title='همگام‌سازیِ ChatGPT-WP',
            store=store,
            sites=[{
                'key': s.get('key'), 'url': s.get('url'), 'active': s.get('active', True),
                'has_password': bool(s.get('user') and s.get('password')),
                'prompts': len(s.get('prompts') or []),
                'files': sum(1 for f in files if f.path.startswith(f"files/{s.get('key')}/")),
            } for s in data.get('sites', [])],
            files_count=files.count(),
            panel_url=self.request.build_absolute_uri('/').rstrip('/'),
        )
        return ctx
