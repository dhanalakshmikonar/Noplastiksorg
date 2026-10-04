import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)


def send_branded_email(*, kind, subject, template, context, reply_to=None):
    """Send a multipart notification without exposing mail details or breaking a workflow."""
    recipient = settings.ADMIN_NOTIFICATION_EMAIL
    if not recipient:
        logger.warning('Skipped %s email notification: recipient is not configured.', kind)
        return False

    try:
        text_body = render_to_string(f'emails/{template}.txt', context)
        html_body = render_to_string(f'emails/{template}.html', context)
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.EMAIL_HOST_USER,
            to=[recipient],
            reply_to=[reply_to] if reply_to else None,
        )
        message.attach_alternative(html_body, 'text/html')
        return message.send(fail_silently=False) == 1
    except Exception:
        # Avoid writing SMTP exception details, which may contain account metadata, to logs.
        logger.warning('Could not send %s email notification.', kind)
        return False
