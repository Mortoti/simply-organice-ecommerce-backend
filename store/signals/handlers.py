from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from store.models import Customer
from core.tasks import send_email_task, send_welcome_email_task  # <-- Add this import
from store.signals import order_created


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_customer_for_new_user(sender, instance, created, **kwargs):
    if created:
        Customer.objects.create(user=instance)
        # Send welcome email
        send_welcome_email_task(instance.id)


@receiver(order_created)
def send_confirmation_on_order_create(sender, order, **kwargs):
    """
    Listens for the 'order_created' signal and passes the
    new order's ID to the Celery task.
    """
    send_email_task(order.id)