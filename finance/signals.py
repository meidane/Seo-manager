"""سیگنال‌های حسابداری.

برای هر همکار یک بابتِ «حقوق <نام همکار>» خودکار ساخته/به‌روزرسانی می‌شود تا:
- در بخشِ بابت‌ها دیده شود و تراکنش‌های حقوقِ او به همان بابت خورده شوند،
- مانده‌ی «کل حساب با همکار» در تبِ حقوق از روی همان تراکنش‌ها محاسبه شود.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


def salary_category_name(colleague):
    return f'حقوق {colleague.full_name}'.strip()


@receiver(post_save, sender='colleagues.Colleague')
def ensure_salary_category(sender, instance, **kwargs):
    from .models import Category
    if not instance.organization_id:
        return
    name = salary_category_name(instance)

    # اگر بابتِ لینک‌شده به این همکار هست، فقط نامش را هم‌گام کن (تغییرِ نامِ همکار)
    cat = Category.all_objects.filter(colleague_id=instance.id).first()
    if cat:
        if cat.name != name:
            # جلوی برخوردِ یکتاییِ (organization, name)
            if not Category.all_objects.filter(
                    organization_id=instance.organization_id, name=name
            ).exclude(pk=cat.pk).exists():
                cat.name = name
                cat.save(update_fields=['name'])
        return

    # وگرنه بساز (یا اگر با همین نام از قبل هست، لینکش کن)
    cat, _ = Category.all_objects.get_or_create(
        organization_id=instance.organization_id, name=name,
        defaults={'is_salary': True, 'color': instance.color or '#FBBF24', 'order': 100})
    if cat.colleague_id != instance.id or not cat.is_salary:
        cat.colleague_id = instance.id
        cat.is_salary = True
        cat.save(update_fields=['colleague', 'is_salary'])
