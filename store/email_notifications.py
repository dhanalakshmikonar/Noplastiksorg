import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)


def send_branded_email(*, kind, subject, recipient, template, context, reply_to=None):
    """Send a multipart Noplastiks email without disrupting the user workflow."""
    recipient = (recipient or '').strip()
    if not recipient:
        logger.warning('Skipped %s email notification: recipient is not configured.', kind)
        return False

    try:
        text_body = render_to_string(f'emails/{template}.txt', context)
        html_body = render_to_string(f'emails/{template}.html', context)
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL or None,
            to=[recipient],
            reply_to=[reply_to] if reply_to else None,
        )
        message.attach_alternative(html_body, 'text/html')
        message.send(fail_silently=False)
        return True
    except Exception:
        logger.exception('Could not send %s email notification.', kind)
        return False
