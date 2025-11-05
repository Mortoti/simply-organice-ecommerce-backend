from celery import shared_task
from django.core.mail import EmailMessage  # <-- Use EmailMessage
from django.template.loader import render_to_string


@shared_task
def send_email_task(subject, template_name, context, from_email, recipient_list):
    """
    A Celery task to send a rendered HTML email.
    """
    try:
        # 1. Render the HTML template with the context
        html_message = render_to_string(template_name, context)

        # 2. Create the email message object
        email = EmailMessage(
            subject=subject,
            body=html_message,  # <-- Use the rendered HTML as the body
            from_email=from_email,
            to=recipient_list
        )

        # 3. Set the content type to HTML
        email.content_subtype = 'html'

        # 4. Send the email
        email.send()

        return f"HTML Email sent successfully to {recipient_list}"
    except Exception as e:
        return f"Error sending HTML email: {e}"