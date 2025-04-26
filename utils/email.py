from django.core.mail import EmailMultiAlternatives, get_connection, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
import logging
import csv
import io

logger = logging.getLogger(__name__)

def send_newsletter(subject, template_name, context, recipient_list, from_email=None):
    """
    Send a newsletter to a list of recipients using a HTML template.
    
    Args:
        subject (str): Email subject
        template_name (str): Path to the HTML template
        context (dict): Context variables for the template
        recipient_list (list): List of email addresses
        from_email (str, optional): Sender email address. Defaults to settings.DEFAULT_FROM_EMAIL.
    
    Returns:
        int: Number of emails sent
    """
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL
    
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)
    
    # Log the sending attempt
    logger.info(f"Attempting to send newsletter '{subject}' to {len(recipient_list)} recipients")
    
    # Send in batches to avoid timeout or memory issues
    batch_size = getattr(settings, 'EMAIL_BATCH_SIZE', 100)
    sent_count = 0
    
    with get_connection() as connection:
        for i in range(0, len(recipient_list), batch_size):
            batch = recipient_list[i:i+batch_size]
            messages = []
            
            for recipient in batch:
                message = EmailMultiAlternatives(
                    subject,
                    text_content,
                    from_email,
                    [recipient],
                    connection=connection
                )
                message.attach_alternative(html_content, "text/html")
                messages.append(message)
            
            # Send all emails in the current batch
            sent = connection.send_messages(messages)
            sent_count += sent
            logger.info(f"Sent batch of {sent} emails")
    
    logger.info(f"Newsletter '{subject}' sent to {sent_count} recipients")
    return sent_count

def send_welcome_email(user_email, user_name=None):
    """
    Send a welcome email to a new subscriber.
    
    Args:
        user_email (str): Recipient's email address
        user_name (str, optional): Recipient's name
    
    Returns:
        bool: True if email was sent, False otherwise
    """
    subject = "Welcome to our Newsletter!"
    context = {
        'user_name': user_name or 'there',
        'current_year': timezone.now().year,
        'unsubscribe_url': f"{settings.SITE_URL}/newsletters/unsubscribe/?email={user_email}"
    }
    
    try:
        send_newsletter(
            subject=subject,
            template_name='newsletter/email/welcome.html',
            context=context,
            recipient_list=[user_email]
        )
        logger.info(f"Welcome email sent to {user_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user_email}: {str(e)}")
        return False

def send_confirmation_email(user_email, confirm_token):
    """
    Send a confirmation email with a token link.
    
    Args:
        user_email (str): Recipient's email address
        confirm_token (str): Confirmation token
    
    Returns:
        bool: True if email was sent, False otherwise
    """
    subject = "Please Confirm Your Email Address"
    confirm_url = f"{settings.SITE_URL}/newsletters/confirm/{confirm_token}/"
    
    try:
        send_mail(
            subject=subject,
            message=f"Please confirm your email address by clicking this link: {confirm_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=render_to_string('newsletter/email/confirm.html', {
                'confirm_url': confirm_url
            })
        )
        logger.info(f"Confirmation email sent to {user_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send confirmation email to {user_email}: {str(e)}")
        return False

def send_unsubscribe_confirmation(user_email):
    """
    Send a confirmation email after unsubscribing.
    
    Args:
        user_email (str): Recipient's email address
    
    Returns:
        bool: True if email was sent, False otherwise
    """
    subject = "You've been unsubscribed from our newsletter"
    
    try:
        send_mail(
            subject=subject,
            message="You have been successfully unsubscribed from our newsletter. We're sorry to see you go!",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=render_to_string('newsletter/email/unsubscribe_confirm.html')
        )
        logger.info(f"Unsubscribe confirmation sent to {user_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send unsubscribe confirmation to {user_email}: {str(e)}")
        return False

def import_subscribers_from_csv(csv_file):
    """
    Import subscribers from a CSV file.
    
    Args:
        csv_file: File-like object containing CSV data
    
    Returns:
        dict: {'imported': count of imported emails, 'errors': list of errors}
    """
    result = {'imported': 0, 'errors': []}
    
    try:
        # Use io.StringIO if csv_file is bytes
        if isinstance(csv_file, bytes):
            csv_file = io.StringIO(csv_file.decode('utf-8'))
        
        reader = csv.reader(csv_file)
        header = next(reader, None)
        
        # Validate header (expected: email, name)
        if not header or 'email' not in [h.lower() for h in header]:
            result['errors'].append("Invalid CSV format. Header must contain 'email'.")
            return result
        
        email_index = [h.lower() for h in header].index('email')
        name_index = [h.lower() for h in header].index('name') if 'name' in [h.lower() for h in header] else None
        
        # Import subscribers
        from news.models import Subscriber  # Import here to avoid circular imports
        
        for i, row in enumerate(reader, start=2):  # Start at 2 to account for header
            if len(row) <= email_index:
                result['errors'].append(f"Row {i}: Invalid format")
                continue
            
            email = row[email_index].strip()
            name = row[name_index].strip() if name_index is not None and len(row) > name_index else None
            
            try:
                subscriber, created = Subscriber.objects.get_or_create(
                    email=email,
                    defaults={'name': name, 'is_active': True}
                )
                
                if created:
                    result['imported'] += 1
                    # Optionally send welcome email
                    send_welcome_email(email, name)
            except Exception as e:
                result['errors'].append(f"Row {i}: {str(e)}")
        
        return result
    except Exception as e:
        result['errors'].append(f"Import failed: {str(e)}")
        return result

def create_subscriber_export():
    """
    Create a CSV export of all active subscribers.
    
    Returns:
        io.StringIO: CSV file-like object
    """
    from newsletter.models import Subscriber  # Import here to avoid circular imports
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Email', 'Name', 'Joined Date'])
    
    # Write subscriber rows
    active_subscribers = Subscriber.objects.filter(is_active=True)
    for subscriber in active_subscribers:
        writer.writerow([
            subscriber.email,
            subscriber.name or '',
            subscriber.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    output.seek(0)
    return output