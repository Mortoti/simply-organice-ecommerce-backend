import threading
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from store.models import Order


def send_email_task(order_id):
    def _send_email():
        try:
            order = Order.objects.get(id=order_id)

            if order.status == Order.STATUS_SHIPPED:
                subject = f'Your Order #{order.id} Has Shipped!'
                template_name = 'order_shipped.html'
            elif order.status == Order.STATUS_COMPLETED:
                subject = f'Your Order #{order.id} is Complete!'
                template_name = 'order_completed.html'
            elif order.status == Order.STATUS_CANCELLED:
                subject = f'Your Order #{order.id} Has Been Cancelled'
                template_name = 'order_cancelled.html'
            else:
                subject = f'Your Simply Organice Order #{order.id} is Confirmed!'
                template_name = 'order_confirmation.html'

            order_items = order.items.all()

            order_items_with_total = []
            total_amount = 0

            for item in order_items:
                item_total = (item.price_at_purchase * item.quantity)
                if item.with_customization:
                    item_total += (item.customization_price_at_purchase * item.quantity)

                item.total_price = item_total
                order_items_with_total.append(item)
                total_amount += item_total

            context = {
                'customer_name': order.customer.user.first_name,
                'order_id': order.id,
                'recipient_name': order.recipient_name,
                'order_items': order_items_with_total,
                'total_amount': total_amount,
            }

            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [order.customer.user.email]
            html_message = render_to_string(template_name, context)

            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=from_email,
                to=recipient_list
            )
            email.content_subtype = 'html'
            email.send()

            print(f"✅ Email for order {order_id} (Status: {order.status}) sent.")
        except Order.DoesNotExist:
            print(f"❌ Error: Order {order_id} does not exist.")
        except Exception as e:
            print(f"❌ Error sending email for order {order_id}: {e}")

    thread = threading.Thread(target=_send_email)
    thread.daemon = True
    thread.start()


def send_welcome_email_task(user_id):
    def _send_welcome():
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)

            subject = 'Welcome to Simply Organice!'
            template_name = 'welcome_email.html'

            context = {
                'first_name': user.first_name or user.username,
            }

            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]
            html_message = render_to_string(template_name, context)

            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=from_email,
                to=recipient_list
            )
            email.content_subtype = 'html'
            email.send()

            print(f"✅ Welcome email sent to {user.email}")
        except Exception as e:
            print(f"❌ Error sending welcome email: {e}")

    thread = threading.Thread(target=_send_welcome)
    thread.daemon = True
    thread.start()