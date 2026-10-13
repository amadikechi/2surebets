import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


# ==================================================================
# PROFILE
# ==================================================================

class Profile(models.Model):
    """Extra per-user settings. Kept separate from auth.User."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text='E.164 format, e.g. +2348012345678. Reserved for future WhatsApp.',
    )
    email_verified = models.BooleanField(
        default=False,
        help_text='Set to True once the user confirms their email address.',
    )
    email_notifications = models.BooleanField(
        default=True,
        help_text='Receive an email when a code is published or settled.',
    )
    whatsapp_notifications = models.BooleanField(
        default=False,
        help_text='Receive WhatsApp messages. Currently disabled — reserved for later.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile: {self.user.username}'


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create a Profile whenever a new User is created."""
    if created:
        Profile.objects.get_or_create(user=instance)


# ==================================================================
# EMAIL VERIFICATION
# ==================================================================

class EmailVerification(models.Model):
    """A one-time token for verifying a user's email address."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_verification',
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    EXPIRY_DAYS = 3

    def __str__(self):
        return f'Verification for {self.user.username}'

    @classmethod
    def generate(cls, user):
        """Create (or replace) a verification token for a user."""
        token = secrets.token_urlsafe(48)
        obj, _ = cls.objects.update_or_create(
            user=user,
            defaults={'token': token, 'verified_at': None},
        )
        return obj

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(days=self.EXPIRY_DAYS)

    @property
    def is_verified(self):
        return self.verified_at is not None


# ==================================================================
# NOTIFICATION LOG
# ==================================================================

class NotificationLog(models.Model):
    """Every notification we try to send. Success and failure both logged."""

    CHANNEL_EMAIL = 'email'
    CHANNEL_WHATSAPP = 'whatsapp'
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, 'Email'),
        (CHANNEL_WHATSAPP, 'WhatsApp'),
    ]

    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_SKIPPED = 'skipped'
    STATUS_CHOICES = [
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_SKIPPED, 'Skipped'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    channel = models.CharField(max_length=12, choices=CHANNEL_CHOICES, default=CHANNEL_EMAIL)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_SENT)
    subject = models.CharField(max_length=200, blank=True)
    body_preview = models.CharField(max_length=200, blank=True)
    error = models.CharField(max_length=500, blank=True)
    related_betcode = models.ForeignKey(
        'betting.BetCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f'{self.user.username} · {self.channel} · {self.status}'