"""فرم افزودن/ویرایش پروژه."""
from django import forms

from colleagues.models import Colleague
from core.jalali import format_jalali, parse_jalali

from .models import Project


class ProjectForm(forms.ModelForm):
    project_types = forms.MultipleChoiceField(
        label='نوع پروژه', choices=Project.TYPE_CHOICES, required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    contract_start = forms.CharField(label='شروع قرارداد (شمسی)', required=False,
                                     widget=forms.TextInput(attrs={'dir': 'ltr', 'placeholder': '۱۴۰۴/۰۵/۰۱', 'class': 'input jdate'}))
    contract_end = forms.CharField(label='پایان قرارداد (شمسی)', required=False,
                                   widget=forms.TextInput(attrs={'dir': 'ltr', 'placeholder': '۱۴۰۵/۰۵/۰۱', 'class': 'input jdate'}))

    class Meta:
        model = Project
        fields = [
            'name', 'logo', 'domain', 'track_keyword_rank', 'color', 'status', 'priority', 'amount',
            'client_name', 'client_phone', 'manager', 'members', 'description',
        ]
        widgets = {
            'members': forms.CheckboxSelectMultiple,
            'priority': forms.NumberInput(attrs={'dir': 'ltr', 'min': 1, 'placeholder': '۱ = بالاترین'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active = Colleague.objects.filter(status=Colleague.ACTIVE)
        self.fields['manager'].queryset = active
        self.fields['manager'].required = False
        self.fields['members'].queryset = active
        if self.instance and self.instance.pk:
            self.fields['project_types'].initial = self.instance.types_list
            if self.instance.contract_start:
                self.fields['contract_start'].initial = format_jalali(self.instance.contract_start, fa_digits=False)
            if self.instance.contract_end:
                self.fields['contract_end'].initial = format_jalali(self.instance.contract_end, fa_digits=False)
        self.fields['description'].widget.attrs.update({'class': 'rich-editor'})
        # مبلغِ قرارداد: ویرگولِ زنده (app.js کلاسِ money؛ روی submit ویرگول‌ها پاک می‌شوند)
        self.fields['amount'].widget.attrs.update({'class': 'input money', 'dir': 'ltr'})

    def clean_description(self):
        from core.htmlsan import clean_html
        return clean_html(self.cleaned_data.get('description', ''))

    def _clean_jdate(self, field):
        value = (self.cleaned_data.get(field) or '').strip()
        if not value:
            return None
        try:
            return parse_jalali(value)
        except (ValueError, TypeError):
            raise forms.ValidationError('تاریخ نامعتبر است. نمونه: ۱۴۰۴/۰۵/۰۱')

    def clean_contract_start(self):
        return self._clean_jdate('contract_start')

    def clean_contract_end(self):
        return self._clean_jdate('contract_end')

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.project_types = ','.join(self.cleaned_data.get('project_types', []))
        obj.contract_start = self.cleaned_data.get('contract_start')
        obj.contract_end = self.cleaned_data.get('contract_end')
        if commit:
            obj.save()
            self.save_m2m()
        return obj
