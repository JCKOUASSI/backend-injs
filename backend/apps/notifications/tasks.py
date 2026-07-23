from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_notification_email(recipient_email, title, message):
    send_mail(
        subject=f'[INJS-LMD] {title}',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@injs.ci',
        recipient_list=[recipient_email],
        fail_silently=True,
    )


@shared_task
def send_push_notification(user_id, title, message, data=None):
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{user_id}',
        {'type': 'notification_message', 'data': {'title': title, 'message': message, 'data': data or {}}},
    )
