# In core/tasks.py

from celery import shared_task
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from store.models import Order  # <-- Import the Order model


@shared_task
def send_email_task(order_id):
    """
    A Celery task to send a rendered HTML email.
    It receives an order_id, fetches all data from the database,
    builds the context, and sends the email.
    """
    try:
        # 1. Get the order from the database using the ID
        order = Order.objects.get(id=order_id)

        # 2. Get all the related items
        order_items = order.items.all()

        # 3. Build the context (This logic moved from the signal to here)
        context = {
            'customer_name': order.customer.user.first_name,
            'order_id': order.id,
            'recipient_name': order.recipient_name,
            'order_items': order_items,
        }

        # 4. Set up the email details
        subject = f'Your Simply Organice Order #{order.id} is Confirmed!'
        template_name = 'order_confirmation.html'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [order.customer.user.email]

        # 5. Render the HTML template
        html_message = render_to_string(template_name, context)

        # 6. Create and send the email
        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=from_email,
            to=recipient_list
        )
        email.content_subtype = 'html'  # Set content type to HTML
        email.send()

        return f"HTML Email for order {order_id} sent successfully."

    except Order.DoesNotExist:
        return f"Error: Order {order_id} does not exist."
    except Exception as e:
        # Log the exception for debugging
        return f"Error sending email for order {order_id}: {e}"