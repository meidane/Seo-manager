"""سیگنال‌های پروژه.

برای هر همکار یک پروژه‌ی «شخصی» خودکار ساخته می‌شود که **فقط خودش** می‌بیند
(گیتِ سراسری در `projects/access.py`). idempotent است.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

PERSONAL_NAME = 'شخصی'


@receiver(post_save, sender='colleagues.Colleague')
def ensure_personal_project(sender, instance, **kwargs):
    if not instance.organization_id:
        return
    from .models import Project
    if Project.all_objects.filter(personal_owner=instance).exists():
        return
    p = Project.all_objects.create(
        organization_id=instance.organization_id,
        name=PERSONAL_NAME, personal_owner=instance, manager=instance,
        color=instance.color or '#8FA0B8', status=Project.ACTIVE)
    p.members.set([instance])
