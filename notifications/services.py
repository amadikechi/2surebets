import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from .models import EmailVerification, NotificationLog

logger = logging.getLogger(__name__)


def send_verification_email(user, request=None):
    """Send the email-verification link to a new user."""
    verification = EmailVerification.generate(user)

    protocol = 'https' if request and request.is_secure() else 'http'
    domain = request.get_host() if request else settings.SITE_DOMAIN
    verify_path = reverse('accounts:verify_email', kwargs={'token': verification.token})
    verify_url = f'{protocol}://{domain}{verify_path}'

    context = {
        'user': user,
        'token': verification.token,
        'protocol': protocol,
        'domain': domain,
        'verify_url': verify_url,
        'site_name': settings.SITE_NAME,
        'site_domain': settings.SITE_DOMAIN,
    }

    subject = render_to_string('notifications/email_verify_subject.txt', context).strip()
    html_body = render_to_string('notifications/email_verify.html', context)
    text_body = render_to_string('notifications/email_verify.txt', context)

    try:
        send_mail(
            subject=subject,
            message=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_body,
            fail_silently=False,
        )
        NotificationLog.objects.create(
            user=user,
            channel=NotificationLog.CHANNEL_EMAIL,
            status=NotificationLog.STATUS_SENT,
            subject=subject,
            body_preview=f'Email verification link sent to {user.email}',
        )
        return True
    except Exception as exc:
        NotificationLog.objects.create(
            user=user,
            channel=NotificationLog.CHANNEL_EMAIL,
            status=NotificationLog.STATUS_FAILED,
            subject=subject,
            body_preview='Verification email failed',
            error=str(exc)[:500],
        )
        logger.exception('Failed to send verification email to %s', user.username)
        return False