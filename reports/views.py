"""ویوهای گزارش‌دهی — صفحه‌ی ساخت (login) + نسخه‌ی عمومی مشتری (بدون login)."""
import json
from datetime import date

import bleach
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView, View

from core.jalali import parse_jalali
from core.models import Attachment
from projects.models import Project
from tasks.models import Task

from .models import BUCKETS, CLIENT_FIELDS, TYPE_TO_BUCKET, Report, ReportItem

# پاکسازی HTML ادیتور توضیحات
ALLOWED_TAGS = ['p', 'br', 'b', 'strong', 'i', 'em', 'u', 'h2', 'h3', 'ul', 'ol',
                'li', 'a', 'img', 'blockquote', 'span', 'div']
ALLOWED_ATTRS = {'a': ['href', 'target', 'rel'], 'img': ['src', 'alt', 'style'],
                 'span': ['style'], 'div': ['style'], 'p': ['style']}


def clean_html(html):
    return bleach.clean(html or '', tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


# ── صفحات ────────────────────────────────────────────────────────────────

class ReportListView(LoginRequiredMixin, ListView):
    model = Report
    template_name = 'reports/list.html'
    context_object_name = 'reports'
    paginate_by = 30

    def get_queryset(self):
        return super().get_queryset().select_related('project')

    def get_context_data(self, **kwargs):
        from finance.models import Invoice
        ctx = super().get_context_data(**kwargs)
        ctx['projects'] = Project.objects.filter(status=Project.ACTIVE)
        ctx['invoices'] = Invoice.objects.select_related('project')
        ctx['page_title'] = 'گزارش‌ها'
        return ctx


class ReportCreateView(LoginRequiredMixin, View):
    """ساخت سریع گزارش با پروژه + بازه، سپس هدایت به صفحه‌ی ساخت."""

    def post(self, request):
        data = request.POST
        try:
            report = Report.objects.create(
                project_id=data['project'],
                invoice_id=data.get('invoice') or None,
                title=data.get('title') or 'گزارش جدید',
                date_from=parse_jalali(data['date_from']),
                date_to=parse_jalali(data['date_to']),
                created_by=request.user,
            )
        except (KeyError, ValueError):
            return redirect('reports:list')
        return redirect(report.get_absolute_url())


class ReportDetailView(LoginRequiredMixin, DetailView):
    model = Report
    template_name = 'reports/detail.html'
    context_object_name = 'report'

    def get_context_data(self, **kwargs):
        from finance.models import Invoice
        ctx = super().get_context_data(**kwargs)
        ctx['groups'] = self.object.grouped_items()
        ctx['client_fields'] = CLIENT_FIELDS
        ctx['visible_fields'] = self.object.visible_fields
        ctx['invoices'] = Invoice.objects.select_related('project')
        ctx['page_title'] = self.object.title
        return ctx


class PublicReportView(DetailView):
    """نسخه‌ی عمومی مشتری — بدون login، فقط فیلدهای مجاز."""

    model = Report
    template_name = 'reports/public.html'
    context_object_name = 'report'
    slug_field = 'public_token'
    slug_url_kwarg = 'token'

    def get_queryset(self):
        return Report.objects.filter(is_public=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['groups'] = self.object.grouped_items()
        # فقط فیلدهای مجاز، به‌ترتیب تعریف
        ctx['fields'] = [(k, lbl) for k, lbl in CLIENT_FIELDS if self.object.sees(k)]
        return ctx


class ReportPreviewView(LoginRequiredMixin, DetailView):
    """پیش‌نمایش دقیقِ آنچه مشتری می‌بیند — برای صاحب گزارش، بدون نیاز به عمومی‌کردن."""

    model = Report
    template_name = 'reports/public.html'
    context_object_name = 'report'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['groups'] = self.object.grouped_items()
        ctx['fields'] = [(k, lbl) for k, lbl in CLIENT_FIELDS if self.object.sees(k)]
        ctx['is_preview'] = True
        return ctx


# ── API ──────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(['GET'])
def pull_tasks(request, pk):
    """تسک‌های بازه، گروه‌بندی‌شده بر اساس نوع، برای انتخاب و افزودن.
    تسک‌های قبلاً افزوده‌شده کنار گذاشته می‌شوند. GET ?from=&to="""
    report = get_object_or_404(Report, pk=pk)
    g = request.GET
    try:
        d_from = parse_jalali(g['from']) if g.get('from') else report.date_from
        d_to = parse_jalali(g['to']) if g.get('to') else report.date_to
    except (ValueError, TypeError):
        d_from, d_to = report.date_from, report.date_to

    added = set(report.items.exclude(task__isnull=True).values_list('task_id', flat=True))
    qs = Task.objects.select_related('assignee','type_def').filter(
        project=report.project, done_date__range=(d_from, d_to), status=Task.DONE
    ).exclude(id__in=added)

    groups = []
    for key, label, types in BUCKETS:
        rows = [{
            'id': t.id, 'title': t.title, 'type_label': t.type_label,
            'color': t.color_rgb, 'assignee': t.assignee.full_name if t.assignee else '',
            'done_date_fa': _fa(t.done_date),
        } for t in qs if t.task_type in types]
        if rows:
            groups.append({'key': key, 'label': label, 'tasks': rows})
    return JsonResponse({'groups': groups})


def _fa(d):
    from core.jalali import format_jalali
    return format_jalali(d) if d else ''


@login_required
@require_http_methods(['POST'])
def add_items(request, pk):
    report = get_object_or_404(Report, pk=pk)
    ids = _body(request).get('task_ids', [])
    start = report.items.count()
    created = 0
    existing = set(report.items.values_list('task_id', flat=True))
    for i, tid in enumerate(ids):
        if tid in existing:
            continue
        ReportItem.objects.create(report=report, task_id=tid, order=start + i)
        created += 1
    return JsonResponse({'ok': True, 'added': created})


@login_required
@require_http_methods(['POST'])
def add_manual(request, pk):
    report = get_object_or_404(Report, pk=pk)
    d = _body(request)
    ReportItem.objects.create(
        report=report, order=report.items.count(),
        override_title=d.get('title', 'ردیف دستی'),
        manual_type=d.get('type', 'other'), manual_url=d.get('url', ''),
    )
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def item_edit(request, pk):
    item = get_object_or_404(ReportItem, pk=pk)
    if request.method == 'DELETE':
        item.delete()
        return JsonResponse({'ok': True})
    d = _body(request)
    if 'override_title' in d:
        item.override_title = d['override_title'] or ''
    if 'override_description' in d:
        item.override_description = clean_html(d['override_description'])
    if 'override_done_date' in d:
        val = d['override_done_date']
        try:
            item.override_done_date = parse_jalali(val) if val else None
        except (ValueError, TypeError):
            pass
    item.save()
    return JsonResponse({'ok': True, 'title': item.eff_title,
                         'done_date': _fa(item.eff_done_date)})


@login_required
@require_http_methods(['POST'])
def reorder(request, pk):
    report = get_object_or_404(Report, pk=pk)
    for i, item_id in enumerate(_body(request).get('order', [])):
        report.items.filter(id=item_id).update(order=i)
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(['PATCH'])
def report_update(request, pk):
    report = get_object_or_404(Report, pk=pk)
    d = _body(request)
    if 'title' in d:
        report.title = d['title']
    if 'description' in d:
        report.description = clean_html(d['description'])
    if 'visible_fields' in d:
        valid = {k for k, _ in CLIENT_FIELDS}
        report.visible_fields = [f for f in d['visible_fields'] if f in valid]
    if 'is_public' in d:
        report.is_public = bool(d['is_public'])
    if 'status' in d:
        report.status = d['status']
    if 'invoice' in d:
        report.invoice_id = d['invoice'] or None
    report.save()
    return JsonResponse({'ok': True, 'public_url': report.public_url(), 'is_public': report.is_public})


@login_required
@require_http_methods(['POST'])
def upload_image(request, pk):
    """آپلود عکس داخل توضیحات؛ به‌عنوان Attachment روی همین گزارش ذخیره می‌شود."""
    report = get_object_or_404(Report, pk=pk)
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'detail': 'فایلی نیست'}, status=400)
    if f.size > 20 * 1024 * 1024:
        return JsonResponse({'detail': 'حجم بیش از ۲۰ مگابایت'}, status=400)
    att = Attachment.objects.create(
        content_type=ContentType.objects.get_for_model(Report), object_id=report.id,
        file=f, original_name=f.name, size=f.size, mime=f.content_type or '',
        uploaded_by=request.user,
    )
    return JsonResponse({'url': att.file.url})
