"""فرم افزودن/ویرایش همکار."""
from django import forms

from core.jalali import format_jalali, parse_jalali

from .models import Colleague


class ColleagueForm(forms.ModelForm):
    roles = forms.MultipleChoiceField(
        label='نقش‌ها',
        choices=Colleague.ROLE_CHOICES,
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
            'status', 'description', 'rate_per_word', 'rate_per_task',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['roles'].initial = self.instance.roles_list
            if self.instance.join_date:
                self.fields['join_date'].initial = format_jalali(
                    self.instance.join_date, fa_digits=False
                )

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
