# escrow/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from decimal import Decimal
import uuid
from main.models import Order, Wallet
from main.views import verify_flutterwave_payment, transfer_to_seller, initialize_flutterwave_payment
from .models import EscrowTransaction, EscrowDispute, EscrowStatusHistory


@login_required
def initiate_escrow(request, order_id):
    """Initiate escrow when order is placed"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    
    if hasattr(order, 'escrow'):
        messages.warning(request, "Escrow already exists for this order")
        return redirect('order_detail', order_id=order.id)
    
    # Calculate escrow fee (2% of order amount)
    escrow_fee = order.total_amount * Decimal('0.02')
    total_amount = order.total_amount + escrow_fee
    
    # Create escrow transaction
    escrow = EscrowTransaction.objects.create(
        transaction_id=f"ESC-{uuid.uuid4().hex[:12].upper()}",
        order=order,
        buyer=request.user,
        seller=order.seller,
        amount=order.total_amount,
        escrow_fee=escrow_fee,
        total_amount=total_amount,
        status='pending_payment'
    )
    
    # Redirect to payment
    return redirect('escrow:payment', escrow_id=escrow.id)


@login_required
def process_escrow_payment(request, escrow_id):
    """Process payment for escrow using Flutterwave"""
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id, buyer=request.user)
    
    if request.method == 'POST':
        # Get transaction ID from Flutterwave callback
        transaction_id = request.POST.get('transaction_id')
        
        # Verify payment with Flutterwave
        verification_result = verify_flutterwave_payment(transaction_id)
        
        if verification_result['success']:
            escrow.status = 'in_escrow'
            escrow.payment_received_at = timezone.now()
            escrow.payment_reference = transaction_id
            escrow.payment_provider = 'flutterwave'
            escrow.save()
            
            # Log status change
            EscrowStatusHistory.objects.create(
                escrow=escrow,
                old_status='pending_payment',
                new_status='in_escrow',
                changed_by=request.user,
                reason='Payment received and verified via Flutterwave'
            )
            
            messages.success(request, "Payment received! Your funds are now in escrow.")
            return redirect('escrow:detail', escrow_id=escrow.id)
        else:
            messages.error(request, f"Payment verification failed: {verification_result.get('message', 'Unknown error')}")
    
    # Initialize Flutterwave payment
    payment_data = initialize_flutterwave_payment(escrow)
    
    context = {
        'escrow': escrow,
        'flutterwave_public_key': settings.FLUTTERWAVE_PUBLIC_KEY,
        'payment_link': payment_data.get('link'),
        'tx_ref': payment_data.get('tx_ref')
    }
    return render(request, 'escrow/payment.html', context)


@login_required
def flutterwave_callback(request):
    """Handle Flutterwave payment callback"""
    transaction_id = request.GET.get('transaction_id')
    tx_ref = request.GET.get('tx_ref')
    status = request.GET.get('status')
    
    if status == 'successful' and transaction_id:
        # Extract escrow ID from tx_ref (format: ESC-XXXXX-escrow_id)
        try:
            escrow_id = tx_ref.split('-')[-1]
            escrow = get_object_or_404(EscrowTransaction, id=escrow_id, buyer=request.user)
            
            # Verify the payment
            verification_result = verify_flutterwave_payment(transaction_id)
            
            if verification_result['success']:
                with transaction.atomic():
                    escrow.status = 'in_escrow'
                    escrow.payment_received_at = timezone.now()
                    escrow.payment_reference = transaction_id
                    escrow.payment_provider = 'flutterwave'
                    escrow.save()
                    
                    # Log status change
                    EscrowStatusHistory.objects.create(
                        escrow=escrow,
                        old_status='pending_payment',
                        new_status='in_escrow',
                        changed_by=request.user,
                        reason='Payment received and verified via Flutterwave'
                    )
                
                messages.success(request, "Payment successful! Your funds are now in escrow.")
                return redirect('escrow:detail', escrow_id=escrow.id)
            else:
                messages.error(request, "Payment verification failed. Please contact support.")
                return redirect('escrow:payment', escrow_id=escrow.id)
        except Exception as e:
            messages.error(request, f"Error processing payment: {str(e)}")
            return redirect('dashboard')
    
    elif status == 'cancelled':
        messages.warning(request, "Payment was cancelled.")
        return redirect('dashboard')
    else:
        messages.error(request, "Payment failed. Please try again.")
        return redirect('dashboard')


@login_required
def mark_as_shipped(request, escrow_id):
    """Seller marks order as shipped"""
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id, seller=request.user)
    
    if escrow.status != 'in_escrow':
        messages.error(request, "Cannot mark as shipped at this stage")
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    if request.method == 'POST':
        tracking_number = request.POST.get('tracking_number')
        
        with transaction.atomic():
            escrow.status = 'shipped'
            escrow.shipped_at = timezone.now()
            escrow.save()
            
            # Update order
            escrow.order.tracking_number = tracking_number
            escrow.order.status = 'shipped'
            escrow.order.save()
            
            # Log status change
            EscrowStatusHistory.objects.create(
                escrow=escrow,
                old_status='in_escrow',
                new_status='shipped',
                changed_by=request.user,
                reason=f'Order shipped with tracking: {tracking_number}'
            )
            
            messages.success(request, "Order marked as shipped!")
        
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    return render(request, 'escrow/mark_shipped.html', {'escrow': escrow})


@login_required
def confirm_delivery(request, escrow_id):
    """Buyer confirms delivery"""
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id, buyer=request.user)
    
    if not escrow.can_buyer_confirm():
        messages.error(request, "Cannot confirm delivery at this stage")
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    if request.method == 'POST':
        with transaction.atomic():
            old_status = escrow.status
            escrow.status = 'delivered'
            escrow.delivered_at = timezone.now()
            escrow.calculate_auto_release_date()  
            escrow.save()
            
            # Log status change
            EscrowStatusHistory.objects.create(
                escrow=escrow,
                old_status=old_status,
                new_status='delivered',
                changed_by=request.user,
                reason='Buyer confirmed delivery'
            )
            
            messages.success(request, 
                f"Delivery confirmed! Funds will be released to seller in {escrow.auto_release_days} days "
                "unless you raise a dispute.")
        
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    return render(request, 'escrow/confirm_delivery.html', {'escrow': escrow})


@login_required
def release_funds(request, escrow_id):
    """Release funds to seller (can be manual or automatic)"""
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)
    
    # Check permissions
    is_buyer = escrow.buyer == request.user
    is_admin = request.user.is_staff
    is_auto_release = (escrow.auto_release_at and 
                       timezone.now() >= escrow.auto_release_at)
    
    if not (is_buyer or is_admin or is_auto_release):
        messages.error(request, "You don't have permission to release funds")
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    if not escrow.can_release_to_seller():
        messages.error(request, "Funds cannot be released at this stage")
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    with transaction.atomic():
        # Transfer funds to seller's wallet/account
        transfer_result = transfer_to_seller(escrow.seller, escrow.amount)
        
        if transfer_result.get('success'):
            escrow.status = 'completed'
            escrow.completed_at = timezone.now()
            escrow.save()
            
            # Log status change
            release_reason = 'Automatic release' if is_auto_release else 'Manual release by buyer'
            EscrowStatusHistory.objects.create(
                escrow=escrow,
                old_status='delivered',
                new_status='completed',
                changed_by=request.user if not is_auto_release else None,
                reason=release_reason
            )
            
            messages.success(request, "Funds have been released to the seller!")
        else:
            messages.error(request, f"Failed to release funds: {transfer_result.get('message')}")
    
    return redirect('escrow:detail', escrow_id=escrow.id)


@login_required
def raise_dispute(request, escrow_id):
    """Raise a dispute"""
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)
    
    # Only buyer or seller can raise dispute
    if request.user not in [escrow.buyer, escrow.seller]:
        messages.error(request, "You cannot raise a dispute for this transaction")
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    # Check if dispute already exists
    if hasattr(escrow, 'dispute'):
        messages.warning(request, "A dispute already exists for this transaction")
        return redirect('escrow:dispute_detail', dispute_id=escrow.dispute.id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason')
        evidence = request.POST.get('evidence')
        
        with transaction.atomic():
            old_status = escrow.status
            
            dispute = EscrowDispute.objects.create(
                escrow=escrow,
                raised_by=request.user,
                reason=reason
            )
            
            # Set evidence based on who raised it
            if request.user == escrow.buyer:
                dispute.buyer_evidence = evidence
            else:
                dispute.seller_evidence = evidence
            dispute.save()
            
            # Update escrow status
            escrow.status = 'disputed'
            escrow.save()
            
            # Log status change
            EscrowStatusHistory.objects.create(
                escrow=escrow,
                old_status=old_status,
                new_status='disputed',
                changed_by=request.user,
                reason=f'Dispute raised: {reason[:100]}'
            )
            
            messages.success(request, "Dispute has been raised. Our team will review it.")
        
        return redirect('escrow:dispute_detail', dispute_id=dispute.id)
    
    return render(request, 'escrow/raise_dispute.html', {'escrow': escrow})


@login_required
def dispute_detail(request, dispute_id):
    """View dispute details"""
    dispute = get_object_or_404(EscrowDispute, id=dispute_id)
    escrow = dispute.escrow
    
    # Check permissions
    if request.user not in [escrow.buyer, escrow.seller] and not request.user.is_staff:
        messages.error(request, "You don't have permission to view this dispute")
        return redirect('dashboard')
    
    context = {
        'dispute': dispute,
        'escrow': escrow,
    }
    return render(request, 'escrow/dispute_detail.html', context)


@login_required
def escrow_detail(request, escrow_id):
    """View escrow details"""
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)
    
    # Check permissions
    if request.user not in [escrow.buyer, escrow.seller] and not request.user.is_staff:
        messages.error(request, "You don't have permission to view this escrow")
        return redirect('dashboard')
    
    context = {
        'escrow': escrow,
        'status_history': escrow.status_history.all()[:10],
        'can_confirm_delivery': escrow.can_buyer_confirm() and request.user == escrow.buyer,
        'can_release': escrow.can_release_to_seller() and request.user == escrow.buyer,
        'can_dispute': escrow.status in ['shipped', 'delivered'] and request.user in [escrow.buyer, escrow.seller],
    }
    return render(request, 'escrow/detail.html', context)