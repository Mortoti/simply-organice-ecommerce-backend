# In store/signals/handlers.py

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from store.models import Customer
from core.tasks import send_email_task       # <-- Import the task
from store.signals import order_created     # <-- Import the custom signal

#
# SIGNAL 1: This creates a Customer profile when a new User registers.
#
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_customer_for_new_user(sender, instance, created, **kwargs):
    if created:
        Customer.objects.create(user=instance)

#
# SIGNAL 2: This sends the new, simplified task.
#
@receiver(order_created)
def send_confirmation_on_order_create(sender, order, **kwargs):
    """
    Listens for the 'order_created' signal and just passes the
    new order's ID to the Celery task.
    """
    # All we do is send the ID. The task will handle the rest.
    send_email_task.delay(order_id=order.id)