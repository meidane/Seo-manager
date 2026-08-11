"""فرم افزودن/ویرایش همکار."""
from django import forms

from accounts.tenancy import get_current_org
from core.jalali import format_jalali, parse_jalali

from .models import Colleague


class ColleagueForm(forms.ModelForm):
    roles = forms.MultipleChoiceField(
        label='نقش‌ها',
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    join_date = forms.CharField(
        label='تاریخ عضویت (شمسی)',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '۱۴۰۴/۰۵/۱۵', 'dir': 'ltr', 'class': 'input jdate'}),
    )

    class Meta:
        model = Colleague
        fields = [
            'full_name', 'avatar', 'color', 'phone', 'email',
            'status', 'description', 'manager', 'needs_review',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # نقش‌ها از کاتالوگِ نقش‌های سازمان می‌آید (تنظیمات → تیم‌ها و نقش‌ها)، نه فهرستِ
        # ثابتِ قدیمی — همان نقش‌هایی که برای دسترسی هم استفاده می‌شوند.
        org = get_current_org()
        self.fields['roles'].choices = (
            [(r.key, r.name) for r in org.roles.all()] if org else [])
        managers = Colleague.objects.filter(status=Colleague.ACTIVE)
        if self.instance and self.instance.pk:
            managers = managers.exclude(pk=self.instance.pk)
            self.fields['roles'].initial = self.instance.roles_list
            if self.instance.join_date:
                self.fields['join_date'].initial = format_jalali(
                    self.instance.join_date, fa_digits=False
                )
        self.fields['manager'].queryset = managers
        self.fields['manager'].required = False
        self.fields['needs_review'].required = False
        self.fields['description'].widget.attrs.update({'class': 'rich-editor'})

    def clean_description(self):
        from core.htmlsan import clean_html
        return clean_html(self.cleaned_data.get('description', ''))

    def clean_join_date(self):
        value = (self.cleaned_data.get('join_date') or '').strip()
        if not value:
            return None
        try:
            return parse_jalali(value)
        except (ValueError, TypeError):
            raise forms.ValidationError('تاریخ نامعتبر است. نمونه: ۱۴۰۴/۰۵/۱۵')

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.roles = ','.join(self.cleaned_data.get('roles', []))
        obj.join_date = self.cleaned_data.get('join_date')
        if commit:
            obj.save()
        return obj
