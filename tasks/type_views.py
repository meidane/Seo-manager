"""بخش مدیریت انواع تسک سفارشی — `/settings/task-types/`.

مستقل از مودال تسک است. اینجا فقط نوع و فیلدهایش تعریف می‌شوند؛ اتصال به مودالِ
ساخت تسک در گام بعد انجام می‌شود (اسکیمای آماده: TaskTypeDef.schema()).
"""
import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView

from accounts.access import require_perm

from .models import KPIChecklistItem, TaskTypeDef, TaskTypeField, TaskTypeKPI


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


def _field_dict(f):
    """همه‌ی فیلدهای قابل‌ویرایشِ یک TaskTypeField — منبعِ واحدِ پاسخِ create/edit
    تا مودالِ ویرایش در فرانت همه را داشته باشد (بدونِ رفرش)."""
    return {
        'id': f.id, 'key': f.key, 'label': f.label,
        'kind': f.kind, 'kind_display': f.get_kind_display(),
        'options': f.options, 'placeholder': f.placeholder,
        'required': f.required, 'required_on_done': f.required_on_done,
        'show_to_client': f.show_to_client, 'is_word_source': f.is_word_source,
        'is_keyword_source': f.is_keyword_source, 'track_keyword_rank': f.track_keyword_rank,
        'is_link_source': f.is_link_source, 'is_page_link': f.is_page_link,
    }


class TaskTypeListView(LoginRequiredMixin, ListView):
    model = TaskTypeDef
    template_name = 'settings/task_types.html'
    context_object_name = 'types'

    def dispatch(self, request, *args, **kwargs):
        require_perm(request, 'manage_task_types')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'انواع تسک'
        return ctx


class TaskTypeEditView(LoginRequiredMixin, DetailView):
    model = TaskTypeDef
    template_name = 'settings/task_type_edit.html'
    context_object_name = 'type_def'

    def dispatch(self, request, *args, **kwargs):
        require_perm(request, 'manage_task_types')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['fields'] = self.object.fields.all()
        ctx['kind_choices'] = TaskTypeField.KIND_CHOICES
        ctx['kpis'] = self.object.kpis.prefetch_related('items')
        ctx['page_title'] = self.object.name
        return ctx


# ── API ──────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def type_create(request):
    require_perm(request, 'manage_task_types')
    d = _body(request)
    name = (d.get('name') or '').strip()
    if not name:
        return JsonResponse({'detail': 'نام لازم است'}, status=400)
    if TaskTypeDef.objects.filter(name=name).exists():
        return JsonResponse({'detail': 'این نام قبلاً وجود دارد'}, status=400)
    t = TaskTypeDef.objects.create(
        name=name, color=d.get('color', '#4183F2'), icon=d.get('icon', ''),
        order=TaskTypeDef.objects.count(), created_by=request.user,
    )
    return JsonResponse({'id': t.id, 'url': t.get_absolute_url()}, status=201)


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def type_edit(request, pk):
    require_perm(request, 'manage_task_types')
    t = get_object_or_404(TaskTypeDef, pk=pk)
    if request.method == 'DELETE':
        t.delete()
        return JsonResponse({'ok': True})
    d = _body(request)
    for f in ('name', 'color', 'icon'):
        if f in d:
            setattr(t, f, d[f])
    if 'is_active' in d:
        t.is_active = bool(d['is_active'])
    if 'requires_review' in d:
        t.requires_review = bool(d['requires_review'])
    t.save()
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(['POST'])
def field_create(request, pk):
    require_perm(request, 'manage_task_types')
    t = get_object_or_404(TaskTypeDef, pk=pk)
    d = _body(request)
    label = (d.get('label') or '').strip()
    if not label:
        return JsonResponse({'detail': 'برچسب لازم است'}, status=400)
    kind = d.get('kind', TaskTypeField.TEXT)
    if kind not in dict(TaskTypeField.KIND_CHOICES):
        return JsonResponse({'detail': 'نوع فیلد نامعتبر'}, status=400)
    f = TaskTypeField.objects.create(
        type_def=t, label=label, kind=kind, options=d.get('options', ''),
        placeholder=d.get('placeholder', ''), required=bool(d.get('required')),
        required_on_done=bool(d.get('required_on_done')),
        show_to_client=bool(d.get('show_to_client', True)),
        is_word_source=bool(d.get('is_word_source')),
        is_keyword_source=bool(d.get('is_keyword_source')),
        track_keyword_rank=bool(d.get('track_keyword_rank')),
        is_link_source=bool(d.get('is_link_source')),
        is_page_link=bool(d.get('is_page_link')),
        order=t.fields.count(),
    )
    return JsonResponse(_field_dict(f), status=201)


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def field_edit(request, pk):
    require_perm(request, 'manage_task_types')
    f = get_object_or_404(TaskTypeField, pk=pk)
    if request.method == 'DELETE':
        f.delete()
        return JsonResponse({'ok': True})
    d = _body(request)
    for attr in ('label', 'kind', 'options', 'placeholder'):
        if attr in d:
            setattr(f, attr, d[attr])
    for attr in ('required', 'required_on_done', 'show_to_client', 'is_word_source',
                 'is_keyword_source', 'track_keyword_rank', 'is_link_source', 'is_page_link'):
        if attr in d:
            setattr(f, attr, bool(d[attr]))
    f.save()
    return JsonResponse(_field_dict(f))


@login_required
@require_http_methods(['POST'])
def field_reorder(request, pk):
    require_perm(request, 'manage_task_types')
    t = get_object_or_404(TaskTypeDef, pk=pk)
    for i, fid in enumerate(_body(request).get('order', [])):
        t.fields.filter(id=fid).update(order=i)
    return JsonResponse({'ok': True})


# ── API: KPI ───────────────────────────────────────────────────────────────

def _kpi(request, pk):
    """KPI با تضمینِ تعلق به سازمانِ جاری."""
    return get_object_or_404(TaskTypeKPI, pk=pk, type_def__organization=request.organization)


@login_required
@require_http_methods(['POST'])
def kpi_create(request, pk):
    require_perm(request, 'manage_task_types')
    t = get_object_or_404(TaskTypeDef, pk=pk)  # org-scoped (TenantManager)
    d = _body(request)
    title = (d.get('title') or '').strip()
    if not title:
        return JsonResponse({'detail': 'عنوان KPI لازم است'}, status=400)
    k = TaskTypeKPI.objects.create(
        type_def=t, title=title, max_score=int(d.get('max_score') or 10),
        description=d.get('description', ''), has_checklist=bool(d.get('has_checklist')),
        order=t.kpis.count())
    return JsonResponse(k.to_dict(), status=201)


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def kpi_edit(request, pk):
    require_perm(request, 'manage_task_types')
    k = _kpi(request, pk)
    if request.method == 'DELETE':
        k.delete()
        return JsonResponse({'ok': True})
    d = _body(request)
    if 'title' in d:
        k.title = (d['title'] or '').strip()
    if 'max_score' in d:
        k.max_score = int(d['max_score'] or 0)
    if 'description' in d:
        k.description = d['description'] or ''
    if 'has_checklist' in d:
        k.has_checklist = bool(d['has_checklist'])
    k.save()
    return JsonResponse(k.to_dict())


@login_required
@require_http_methods(['POST'])
def kpi_item_create(request, pk):
    require_perm(request, 'manage_task_types')
    k = _kpi(request, pk)
    d = _body(request)
    title = (d.get('title') or '').strip()
    if not title:
        return JsonResponse({'detail': 'عنوان آیتم لازم است'}, status=400)
    it = KPIChecklistItem.objects.create(
        kpi=k, title=title, score=int(d.get('score') or 0),
        description=d.get('description', ''), order=k.items.count())
    return JsonResponse({'id': it.id, 'kpi': k.to_dict()}, status=201)


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def kpi_item_edit(request, pk):
    require_perm(request, 'manage_task_types')
    it = get_object_or_404(KPIChecklistItem, pk=pk, kpi__type_def__organization=request.organization)
    if request.method == 'DELETE':
        kpi = it.kpi
        it.delete()
        return JsonResponse({'ok': True, 'kpi': kpi.to_dict()})
    d = _body(request)
    if 'title' in d:
        it.title = (d['title'] or '').strip()
    if 'score' in d:
        it.score = int(d['score'] or 0)
    if 'description' in d:
        it.description = d['description'] or ''
    it.save()
    return JsonResponse({'ok': True, 'kpi': it.kpi.to_dict()})
