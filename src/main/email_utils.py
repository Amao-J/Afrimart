# main/email_utils.py

from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def send_order_confirmation_email(order):
    """
    Send order confirmation email to buyer
    From: orders@Afrimart.africa
    """
    try:
        subject = f'Order Confirmation - #{order.id} - Afrimart'
        
        context = {
            'order': order,
            'buyer': order.buyer,
            'items': order.items.all(),
            'site_url': settings.SITE_URL,
            'support_email': settings.SUPPORT_EMAIL,
        }
        
        html_content = render_to_string('emails/order_confirmation.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=f'Afrimart Orders <{settings.ORDERS_EMAIL}>',
            to=[order.buyer.email],
            reply_to=[settings.SUPPORT_EMAIL],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f'Order confirmation email sent to {order.buyer.email} for order #{order.id}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send order confirmation email: {str(e)}')
        return False


def send_payment_confirmation_email(order):
    """
    Send payment confirmation email to buyer
  
    """
    try:
        subject = f'Payment Received - Order #{order.id} - Afrimart'
        
        context = {
            'order': order,
            'buyer': order.buyer,
            'site_url': settings.SITE_URL,
        }
        
        html_content = render_to_string('emails/payment_confirmation.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=f'Afrimart Orders <{settings.ORDERS_EMAIL}>',
            to=[order.buyer.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f'Payment confirmation sent to {order.buyer.email}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send payment confirmation: {str(e)}')
        return False


def send_order_shipped_email(order):
    """
    Send order shipped notification to buyer
    From: orders@Afrimart.africa
    """
    try:
        subject = f'Your Order Has Been Shipped - #{order.id}'
        
        context = {
            'order': order,
            'buyer': order.buyer,
            'tracking_number': order.tracking_number,
            'site_url': settings.SITE_URL,
        }
        
        html_content = render_to_string('emails/order_shipped.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=f'Afrimart Orders <{settings.ORDERS_EMAIL}>',
            to=[order.buyer.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f'Shipped notification sent for order #{order.id}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send shipped notification: {str(e)}')
        return False


def send_escrow_payment_received_email(escrow):
    """
    Notify buyer that escrow payment was received
   
    """
    try:
        subject = f'Escrow Payment Received - {escrow.transaction_id}'
        
        context = {
            'escrow': escrow,
            'buyer': escrow.buyer,
            'seller': escrow.seller,
            'site_url': settings.SITE_URL,
        }
        
        html_content = render_to_string('emails/escrow_payment_received.html', context)
        text_content = strip_tags(html_content)
        
        # Email to buyer
        email_buyer = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=f'Afrimart Escrow <{settings.ESCROW_EMAIL}>',
            to=[escrow.buyer.email],
        )
        email_buyer.attach_alternative(html_content, "text/html")
        email_buyer.send(fail_silently=False)
        
        # Email to seller
        seller_subject = f'New Escrow Order - {escrow.transaction_id}'
        email_seller = EmailMultiAlternatives(
            subject=seller_subject,
            body=text_content,
            from_email=f'Afrimart Escrow <{settings.ESCROW_EMAIL}>',
            to=[escrow.seller.email],
        )
        email_seller.attach_alternative(html_content, "text/html")
        email_seller.send(fail_silently=False)
        
        logger.info(f'Escrow payment notification sent for {escrow.transaction_id}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send escrow payment notification: {str(e)}')
        return False


def send_escrow_shipped_email(escrow):
    """
    Notify buyer that order has been shipped
    From: escrow@afrimart.africa
    """
    try:
        subject = f'Your Escrow Order Has Been Shipped - {escrow.transaction_id}'
        
        context = {
            'escrow': escrow,
            'buyer': escrow.buyer,
            'tracking_number': escrow.order.tracking_number,
            'site_url': settings.SITE_URL,
        }
        
        html_content = render_to_string('emails/escrow_shipped.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=f'Afrimart Escrow <{settings.ESCROW_EMAIL}>',
            to=[escrow.buyer.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f'Escrow shipped notification sent to {escrow.buyer.email}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send escrow shipped notification: {str(e)}')
        return False


def send_escrow_delivered_email(escrow):
    """
    Notify seller that delivery was confirmed
    From: escrow@Afrimart.africa
    """
    try:
        subject = f'Delivery Confirmed - {escrow.transaction_id}'
        
        context = {
            'escrow': escrow,
            'seller': escrow.seller,
            'auto_release_days': escrow.auto_release_days,
            'auto_release_at': escrow.auto_release_at,
            'site_url': settings.SITE_URL,
        }
        
        html_content = render_to_string('emails/escrow_delivered.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=f'Afrimart Escrow <{settings.ESCROW_EMAIL}>',
            to=[escrow.seller.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f'Delivery confirmation sent to seller for {escrow.transaction_id}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send delivery confirmation: {str(e)}')
        return False


def send_escrow_funds_released_email(escrow):
    """
    Notify seller that funds have been released
    From: escrow@Afrimart.africa
    """
    try:
        subject = f'Escrow Funds Released - ₦{escrow.amount:,.2f}'
        
        context = {
            'escrow': escrow,
            'seller': escrow.seller,
            'amount': escrow.amount,
            'site_url': settings.SITE_URL,
        }
        
        html_content = render_to_string('emails/escrow_funds_released.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=f'Afrimart Escrow <{settings.ESCROW_EMAIL}>',
            to=[escrow.seller.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f'Funds released notification sent to {escrow.seller.email}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send funds released notification: {str(e)}')
        return False


def send_escrow_dispute_email(dispute):
    """
    Notify both parties about dispute
    From: escrow@Afrimart.africa
    """
    try:
        escrow = dispute.escrow
        subject = f'Dispute Raised - {escrow.transaction_id}'
        
        context = {
            'dispute': dispute,
            'escrow': escrow,
            'site_url': settings.SITE_URL,
        }
        
        html_content = render_to_string('emails/escrow_dispute.html', context)
        text_content = strip_tags(html_content)
        
        # Email to both buyer and seller
        recipients = [escrow.buyer.email, escrow.seller.email]
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=f'Afrimart Escrow <{settings.ESCROW_EMAIL}>',
            to=recipients,
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f'Dispute notification sent for {escrow.transaction_id}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send dispute notification: {str(e)}')
        return False


def send_order_cancelled_email(order):
    """
    Notify buyer that order was cancelled
    From: orders@Afrimart.africa
    """
    try:
        subject = f'Order Cancelled - #{order.id}'
        
        context = {
            'order': order,
            'buyer': order.buyer,
            'site_url': settings.SITE_URL,
            'support_email': settings.SUPPORT_EMAIL,
        }
        
        html_content = render_to_string('emails/order_cancelled.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=f'Afrimart Orders <{settings.ORDERS_EMAIL}>',
            to=[order.buyer.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f'Cancellation email sent for order #{order.id}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send cancellation email: {str(e)}')
        return False


def send_welcome_email(user):
    """
    Send welcome email to new users
    From: noreply@Afrimart.africa
    """
    try:
        subject = 'Welcome to Afrimart Africa!'
        
        context = {
            'user': user,
            'site_url': settings.SITE_URL,
        }
        
        html_content = render_to_string('emails/welcome.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=f'Afrimart Africa <{settings.NOREPLY_EMAIL}>',
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f'Welcome email sent to {user.email}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send welcome email: {str(e)}')
        return False


def send_low_stock_alert(product):
    """
    Alert admin about low stock
    From: noreply@Afrimart.africa
    To: admin@Afrimart.africa
    """
    try:
        subject = f'Low Stock Alert - {product.name}'
        
        message = f"""
        Product: {product.name}
        Current Stock: {product.stock}
        Price: ₦{product.price:,.2f}
        
        Please restock this product soon.
        
        View product: {settings.SITE_URL}/admin/main/product/{product.id}/change/
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.NOREPLY_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=False,
        )
        
        logger.info(f'Low stock alert sent for {product.name}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send stock alert: {str(e)}')
        return False


def send_admin_notification(subject, message):
 
    try:
        send_mail(
            subject=f'[Admin Alert] {subject}',
            message=message,
            from_email=settings.NOREPLY_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=False,
        )
        
        logger.info(f'Admin notification sent: {subject}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send admin notification: {str(e)}')
        return False





def send_escrow_notification(user, notification_type, escrow):
    """
    Send email notification for escrow events
    
    notification_type options:
    - 'payment_confirmed' (buyer)
    - 'payment_received' (seller)
    - 'order_shipped' (buyer)
    - 'funds_released' (seller)
    """
    
    subject_map = {
        'payment_confirmed': f'Payment Confirmed - Order #{escrow.order.id}',
        'payment_received': f'New Escrow Payment - Order #{escrow.order.id}',
        'order_shipped': f'Order Shipped - {escrow.transaction_id}',
        'funds_released': f'Payment Released - ₦{escrow.amount:,.2f}',
    }
    
    message_map = {
        'payment_confirmed': f'Your payment of ₦{escrow.total_amount:,.2f} has been confirmed and is now held securely in escrow.',
        'payment_received': f'A buyer has paid ₦{escrow.amount:,.2f} into escrow for Order #{escrow.order.id}. Please ship the order.',
        'order_shipped': f'Your order has been shipped! Track: {escrow.order.tracking_number or "N/A"}',
        'funds_released': f'₦{escrow.amount:,.2f} has been released to your wallet.',
    }
    
    subject = subject_map.get(notification_type, 'Afrimart Notification')
    message = message_map.get(notification_type, '')
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as e:
        # Log error but don't break the transaction
        print(f"Email notification failed: {e}")


def send_order_notification(user, notification_type, order):
    """
    Send email notification for regular order events
    
    notification_type options:
    - 'payment_confirmed' (buyer)
    - 'new_order' (seller)
    - 'order_shipped' (buyer)
    """
    
    subject_map = {
        'payment_confirmed': f'Payment Confirmed - Order #{order.id}',
        'new_order': f'New Order Received - #{order.id}',
        'order_shipped': f'Order Shipped - #{order.id}',
    }
    
    message_map = {
        'payment_confirmed': f'Your payment for Order #{order.id} has been confirmed. Total: ₦{order.total_amount:,.2f}',
        'new_order': f'You have a new order #{order.id} worth ₦{order.total_amount:,.2f}. Please prepare for shipping.',
        'order_shipped': f'Your order #{order.id} has been shipped!',
    }
    
    subject = subject_map.get(notification_type, 'Afrimart Notification')
    message = message_map.get(notification_type, '')
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Email notification failed: {e}")


