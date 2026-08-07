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

from .models import TaskTypeDef, TaskTypeField


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


class TaskTypeListView(LoginRequiredMixin, ListView):
    model = TaskTypeDef
    template_name = 'settings/task_types.html'
    context_object_name = 'types'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'انواع تسک'
        return ctx


class TaskTypeEditView(LoginRequiredMixin, DetailView):
    model = TaskTypeDef
    template_name = 'settings/task_type_edit.html'
    context_object_name = 'type_def'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['fields'] = self.object.fields.all()
        ctx['kind_choices'] = TaskTypeField.KIND_CHOICES
        ctx['page_title'] = self.object.name
        return ctx


# ── API ──────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def type_create(request):
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
    t.save()
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(['POST'])
def field_create(request, pk):
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
        show_to_client=bool(d.get('show_to_client', True)), order=t.fields.count(),
    )
    return JsonResponse({'id': f.id, 'key': f.key, 'label': f.label,
                         'kind': f.get_kind_display(), 'required': f.required,
                         'show_to_client': f.show_to_client}, status=201)


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def field_edit(request, pk):
    f = get_object_or_404(TaskTypeField, pk=pk)
    if request.method == 'DELETE':
        f.delete()
        return JsonResponse({'ok': True})
    d = _body(request)
    for attr in ('label', 'kind', 'options', 'placeholder'):
        if attr in d:
            setattr(f, attr, d[attr])
    if 'required' in d:
        f.required = bool(d['required'])
    if 'show_to_client' in d:
        f.show_to_client = bool(d['show_to_client'])
    f.save()
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(['POST'])
def field_reorder(request, pk):
    t = get_object_or_404(TaskTypeDef, pk=pk)
    for i, fid in enumerate(_body(request).get('order', [])):
        t.fields.filter(id=fid).update(order=i)
    return JsonResponse({'ok': True})
