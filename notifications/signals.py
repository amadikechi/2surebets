from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from betting.models import BetCode


@receiver(pre_save, sender=BetCode)
def betcode_track_previous_result(sender, instance, **kwargs):
    """Stash the previous result so post_save can compare."""
    if instance.pk:
        try:
            previous = BetCode.objects.get(pk=instance.pk)
            instance._previous_result = previous.result
        except BetCode.DoesNotExist:
            instance._previous_result = None
    else:
        instance._previous_result = None


@receiver(post_save, sender=BetCode)
def betcode_notify_on_settle(sender, instance, created, **kwargs):
    """Notifications disabled until we have a proper send rhythm."""
    return  # ← remove this line to re-enable