"""ویوهای همکاران — CRUD کامل + غیرفعال/فعال‌سازی."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from .forms import ColleagueForm
from .models import Colleague


class ColleagueListView(LoginRequiredMixin, ListView):
    model = Colleague
    template_name = 'colleagues/list.html'
    context_object_name = 'colleagues'
    paginate_by = 24

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        if query:
            qs = qs.filter(Q(full_name__icontains=query) | Q(email__icontains=query))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'همکاران'
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class ColleagueDetailView(LoginRequiredMixin, DetailView):
    model = Colleague
    template_name = 'colleagues/detail.html'
    context_object_name = 'colleague'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = self.object.full_name
        return ctx


class ColleagueCreateView(LoginRequiredMixin, CreateView):
    model = Colleague
    form_class = ColleagueForm
    template_name = 'colleagues/form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'همکار جدید'
        ctx['is_edit'] = False
        return ctx


class ColleagueUpdateView(LoginRequiredMixin, UpdateView):
    model = Colleague
    form_class = ColleagueForm
    template_name = 'colleagues/form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'ویرایش {self.object.full_name}'
        ctx['is_edit'] = True
        return ctx


class ColleagueArchiveView(LoginRequiredMixin, View):
    """غیرفعال‌سازی (بدون حذف واقعی)."""

    def post(self, request, pk):
        colleague = get_object_or_404(Colleague, pk=pk)
        colleague.archive()
        return redirect(colleague.get_absolute_url())


class ColleagueRestoreView(LoginRequiredMixin, View):
    """فعال‌سازی مجدد."""

    def post(self, request, pk):
        colleague = get_object_or_404(Colleague, pk=pk)
        colleague.restore()
        return redirect(colleague.get_absolute_url())
