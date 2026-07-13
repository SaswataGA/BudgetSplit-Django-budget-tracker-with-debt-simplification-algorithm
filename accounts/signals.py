from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Whenever a User is saved, ensure a matching Profile exists.

    Using a signal here (rather than requiring every place that creates
    a User to remember to also create a Profile) means it's structurally
    impossible to end up with a User that has no Profile — including
    Users created via `createsuperuser`, the admin panel, or `shell`,
    not just through our own registration view.
    """
    if created:
        Profile.objects.create(user=instance)
    else:
        # Profile might not exist yet for users created before this
        # signal existed (e.g. via a data migration) — get_or_create
        # keeps this robust rather than assuming it's always there.
        Profile.objects.get_or_create(user=instance)
