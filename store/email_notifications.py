import logging

from django.conf import settings
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)


def send_branded_email(*, kind, subject, template, context, reply_to=None):
    """Send a multipart notification without exposing mail details or breaking a workflow."""
    recipient = settings.ADMIN_EMAIL
    api_key = settings.RESEND_API_KEY
    sender = settings.RESEND_FROM_EMAIL
    if not recipient or not api_key or not sender:
        logger.warning('Skipped %s email notification: email configuration is incomplete.', kind)
        return False

    try:
        import resend

        text_body = render_to_string(f'emails/{template}.txt', context)
        html_body = render_to_string(f'emails/{template}.html', context)
        resend.api_key = api_key
        params = {
            'from': sender,
            'to': [recipient],
            'subject': subject,
            'html': html_body,
            'text': text_body,
        }
        if reply_to:
            params['reply_to'] = reply_to

        response = resend.Emails.send(params)
        email_id = (
            response.get('id') if isinstance(response, dict)
            else getattr(response, 'id', None)
        )
        if not email_id:
            logger.warning('Resend did not accept the %s email notification.', kind)
            return False
        return True
    except Exception:
        # Avoid logging provider responses or exception text that could contain sensitive data.
        logger.warning('Could not send %s email notification.', kind)
        return False
