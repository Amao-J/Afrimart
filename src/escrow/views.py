# escrow/views.py
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal
import uuid
from django.conf import settings 
from main.models import Order, Wallet, WalletTransaction
from .models import EscrowTransaction, EscrowDispute, EscrowStatusHistory
from main.email_utils import send_escrow_notification, send_order_notification


@login_required
def escrow_dashboard(request):
    """Dashboard for buyer's and seller's escrow transactions"""
    # Get buyer's escrow transactions
    buyer_transactions = EscrowTransaction.objects.filter(
        buyer=request.user
    ).select_related('order', 'seller').order_by('-created_at')
    
    # Get seller's escrow transactions
    seller_transactions = EscrowTransaction.objects.filter(
        seller=request.user
    ).select_related('order', 'buyer').order_by('-created_at')
    
    # Calculate statistics
    buyer_stats = {
        'total_held': buyer_transactions.filter(
            status__in=['in_escrow', 'shipped', 'delivered']
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'total_released': buyer_transactions.filter(status='completed').count(),
        'pending_confirmation': buyer_transactions.filter(status='shipped').count(),
        'in_escrow': buyer_transactions.filter(status='in_escrow').count(),
    }
    
    seller_stats = {
        'total_pending': seller_transactions.filter(
            status__in=['in_escrow', 'shipped', 'delivered']
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'total_received': seller_transactions.filter(status='completed').count(),
        'awaiting_delivery': seller_transactions.filter(status='shipped').count(),
        'to_ship': seller_transactions.filter(status='in_escrow').count(),
    }
    
    context = {
        'buyer_transactions': buyer_transactions[:10],
        'seller_transactions': seller_transactions[:10],
        'buyer_stats': buyer_stats,
        'seller_stats': seller_stats,
    }
    
    return render(request, 'escrow/dashboard.html', context)

@login_required
def initiate_escrow(request, order_id):
    """Initiate escrow when order is placed"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    
    if hasattr(order, 'escrow'):
        messages.warning(request, "Escrow already exists for this order")
        return redirect('order_detail', order_id=order.id)
    
    # Calculate escrow fee (2.5% of order amount)
    escrow_fee = order.total_amount * Decimal('0.025')
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
    
    # Log initial status
    EscrowStatusHistory.objects.create(
        escrow=escrow,
        old_status='',
        new_status='pending_payment',
        changed_by=request.user,
        reason='Escrow transaction initiated'
    )
    
    send_escrow_notification(escrow.buyer, 'escrow_initiated', escrow)
    send_escrow_notification(escrow.seller, 'escrow_initiated', escrow)
    
    messages.success(request, "Escrow transaction created. Please complete payment.")
    return redirect('escrow:payment', escrow_id=escrow.id)


@login_required
def process_escrow_payment(request, escrow_id):
    """Process payment for escrow using Flutterwave"""
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id, buyer=request.user)
    
    if escrow.status != 'pending_payment':
        messages.info(request, "This escrow has already been paid.")
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    # Import from main.views
    from main.views import initialize_flutterwave_payment
    
    # Initialize Flutterwave payment
    payment_data = initialize_flutterwave_payment(escrow)
    
    if not payment_data.get('success'):
        messages.error(request, f"Payment initialization failed: {payment_data.get('message')}")
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    context = {
        'escrow': escrow,
        'order': escrow.order,
        'flutterwave_public_key': getattr(settings, 'FLUTTERWAVE_PUBLIC_KEY', ''),
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
        try:
            # Extract escrow ID from tx_ref
            escrow_id = tx_ref.split('-')[-1]
            escrow = get_object_or_404(EscrowTransaction, id=escrow_id, buyer=request.user)
            
            # Import verification function
            from main.views import verify_flutterwave_payment
            
            # Verify payment with Flutterwave
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
                    
                    # Update order status
                    escrow.order.payment_status = 'paid'
                    escrow.order.save()
                
                messages.success(request, "Payment successful! Your funds are now safely held in escrow.")
                return redirect('escrow:detail', escrow_id=escrow.id)
            else:
                messages.error(request, f"Payment verification failed: {verification_result.get('message')}")
                return redirect('escrow:payment', escrow_id=escrow.id)
        except Exception as e:
            messages.error(request, f"Error processing payment: {str(e)}")
            return redirect('escrow:dashboard')
    
    elif status == 'cancelled':
        messages.warning(request, "Payment was cancelled.")
        return redirect('escrow:dashboard')
    else:
        messages.error(request, "Payment failed. Please try again.")
        return redirect('escrow:dashboard')


@login_required
def mark_as_shipped(request, escrow_id):
    """Seller marks order as shipped"""
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id, seller=request.user)
    
    if escrow.status != 'in_escrow':
        messages.error(request, "Cannot mark as shipped at this stage")
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    if request.method == 'POST':
        tracking_number = request.POST.get('tracking_number', '')
        
        with transaction.atomic():
            escrow.status = 'shipped'
            escrow.shipped_at = timezone.now()
            escrow.save()
            
            # Update order
            if tracking_number:
                escrow.order.tracking_number = tracking_number
            escrow.order.status = 'shipped'
            escrow.order.save()
            
            # Log status change
            EscrowStatusHistory.objects.create(
                escrow=escrow,
                old_status='in_escrow',
                new_status='shipped',
                changed_by=request.user,
                reason=f'Order shipped{" with tracking: " + tracking_number if tracking_number else ""}'
            )
            
            messages.success(request, "Order marked as shipped! Buyer will be notified.")
        
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    return render(request, 'escrow/mark_shipped.html', {'escrow': escrow})

@login_required
def escrow_transaction_detail(request, transaction_id):
    """View details of a specific escrow transaction"""
    
    try:
        transaction = EscrowTransaction.objects.get(transaction_id=transaction_id)
    except EscrowTransaction.DoesNotExist:
        transaction = get_object_or_404(EscrowTransaction, id=transaction_id)
    
  
    if request.user not in [transaction.buyer, transaction.seller] and not request.user.is_staff:
        messages.error(request, "You don't have permission to view this transaction.")
        return redirect('escrow:dashboard')
    
    
    dispute = EscrowDispute.objects.filter(escrow=transaction).first()
    
  
    status_history = EscrowStatusHistory.objects.filter(
        escrow=transaction
    ).order_by('-created_at')[:10]
    
    context = {
        'transaction': transaction,
        'escrow': transaction,  
        'dispute': dispute,
        'status_history': status_history,
        'is_buyer': request.user == transaction.buyer,
        'is_seller': request.user == transaction.seller,
        'can_confirm_delivery': transaction.status == 'shipped' and request.user == transaction.buyer,
        'can_release': transaction.status in ['delivered', 'shipped'] and request.user == transaction.buyer,
        'can_dispute': transaction.status in ['shipped', 'delivered', 'in_escrow'] and request.user in [transaction.buyer, transaction.seller],
        'can_ship': transaction.status == 'in_escrow' and request.user == transaction.seller,
    }
    
    return render(request, 'escrow/transaction_detail.html', context)


@login_required
def confirm_delivery(request, escrow_id):
    """Buyer confirms delivery and releases payment to seller"""
    if request.method == 'POST':
        escrow = get_object_or_404(
            EscrowTransaction,
            id=escrow_id,
            buyer=request.user
        )
        
        if escrow.status not in ['shipped', 'delivered']:
            messages.error(request, 'Cannot confirm delivery at this stage')
            return redirect('escrow:detail', escrow_id=escrow.id)
        
        with transaction.atomic():
            old_status = escrow.status
            escrow.status = 'delivered'
            escrow.delivered_at = timezone.now()
            
            
            from datetime import timedelta
            escrow.auto_release_at = timezone.now() + timedelta(days=7)
            escrow.save()
            
            # Update order status
            escrow.order.status = 'delivered'
            escrow.order.save()
            
            # Log status change
            EscrowStatusHistory.objects.create(
                escrow=escrow,
                old_status=old_status,
                new_status='delivered',
                changed_by=request.user,
                reason='Buyer confirmed delivery'
            )
            
            messages.success(
                request,
                'Delivery confirmed! Funds will be released to seller in 14 days '
                'unless you raise a dispute. You can release funds immediately if satisfied.'
            )
        
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    return redirect('escrow:dashboard')


@login_required
def initiate_dispute(request, escrow_id):
    """Buyer or seller initiates a dispute"""
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)
    
    # Only buyer or seller can raise dispute
    if request.user not in [escrow.buyer, escrow.seller]:
        messages.error(request, "You cannot raise a dispute for this transaction")
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    # Check if already disputed
    if escrow.status == 'disputed':
        messages.warning(request, "This transaction is already under dispute")
        existing_dispute = EscrowDispute.objects.filter(escrow=escrow).first()
        if existing_dispute:
            return redirect('escrow:dispute_detail', dispute_id=existing_dispute.id)
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason')
        evidence = request.POST.get('evidence')
        
        if not reason or not evidence:
            messages.error(request, 'Please provide both reason and evidence')
            dispute_reasons = EscrowDispute.DISPUTE_REASON_CHOICES
            return render(request, 'escrow/raise_dispute.html', {
                'escrow': escrow,
                'transaction': escrow,
                'dispute_reasons': dispute_reasons,
            })
        
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
            
            messages.success(
                request,
                'Dispute has been raised. Our support team will review it within 24-48 hours.'
            )
        
        return redirect('escrow:dispute_detail', dispute_id=dispute.id)
    
    dispute_reasons = EscrowDispute.DISPUTE_REASON_CHOICES
    context = {
        'escrow': escrow,
        'transaction': escrow,
        'dispute_reasons': dispute_reasons,
    }
    
    return render(request, 'escrow/raise_dispute.html', context)


@login_required
def request_refund(request, escrow_id):
    """Quick refund request"""
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id, buyer=request.user)
    
    if escrow.status not in ['in_escrow', 'shipped', 'delivered', 'disputed']:
        messages.error(request, 'Cannot request refund for this transaction.')
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    if request.method == 'POST':
        with transaction.atomic():
            # Get or create buyer wallet
            buyer_wallet, _ = Wallet.objects.get_or_create(user=escrow.buyer)
            
            # Credit buyer wallet (full amount including escrow fee)
            buyer_wallet.credit(escrow.total_amount)
            
            # Create wallet transaction record
            WalletTransaction.objects.create(
                wallet=buyer_wallet,
                amount=escrow.total_amount,
                transaction_type='escrow_refund',
                description=f'Escrow refund for Order #{escrow.order.id}',
                reference=escrow.transaction_id
            )
            
            # Update escrow status
            old_status = escrow.status
            escrow.status = 'refunded'
            escrow.refunded_at = timezone.now()
            escrow.save()
            
            # Update order
            escrow.order.payment_status = 'refunded'
            escrow.order.status = 'cancelled'
            escrow.order.save()
            
            # Log status change
            EscrowStatusHistory.objects.create(
                escrow=escrow,
                old_status=old_status,
                new_status='refunded',
                changed_by=request.user,
                reason='Refund requested by buyer'
            )
            
            messages.success(
                request,
                f'Refund of ₦{escrow.total_amount:,.2f} processed successfully. '
                'Funds have been credited to your wallet.'
            )
        
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    return redirect('escrow:dashboard')


@login_required
def release_funds(request, escrow_id):
    """Release funds to seller"""
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)
    
    # Check permissions
    is_buyer = escrow.buyer == request.user
    is_admin = request.user.is_staff
    
    if not (is_buyer or is_admin):
        messages.error(request, "You don't have permission to release funds")
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    if escrow.status not in ['delivered', 'shipped']:
        messages.error(request, "Funds cannot be released at this stage")
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    if request.method == 'POST':
        with transaction.atomic():
            # Get or create seller wallet
            seller_wallet, _ = Wallet.objects.get_or_create(user=escrow.seller)
            
            # Credit seller wallet
            seller_wallet.credit(escrow.amount)
            
            # Create wallet transaction record
            WalletTransaction.objects.create(
                wallet=seller_wallet,
                amount=escrow.amount,
                transaction_type='escrow_release',
                description=f'Escrow payment released for Order #{escrow.order.id}',
                reference=escrow.transaction_id
            )
            
            # Update escrow status
            old_status = escrow.status
            escrow.status = 'completed'
            escrow.completed_at = timezone.now()
            escrow.save()
            
            # Update order
            escrow.order.payment_status = 'paid'
            escrow.order.status = 'delivered'
            escrow.order.save()
            
            # Log status change
            EscrowStatusHistory.objects.create(
                escrow=escrow,
                old_status=old_status,
                new_status='completed',
                changed_by=request.user,
                reason='Funds released to seller'
            )
            
            messages.success(request, f"₦{escrow.amount:,.2f} has been released to the seller!")
        
        return redirect('escrow:detail', escrow_id=escrow.id)
    
    return render(request, 'escrow/release_confirm.html', {'escrow': escrow})


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
        'is_buyer': request.user == escrow.buyer,
        'is_seller': request.user == escrow.seller,
    }
    return render(request, 'escrow/dispute_detail.html', context)


@login_required
def escrow_history(request):
    """View full escrow transaction history"""
    user_type = request.GET.get('type', 'buyer')  # buyer or seller
    
    if user_type == 'buyer':
        transactions = EscrowTransaction.objects.filter(
            buyer=request.user
        ).select_related('order', 'seller').order_by('-created_at')
    else:
        transactions = EscrowTransaction.objects.filter(
            seller=request.user
        ).select_related('order', 'buyer').order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        transactions = transactions.filter(status=status_filter)
    
    context = {
        'transactions': transactions,
        'user_type': user_type,
        'status_filter': status_filter,
    }
    
    return render(request, 'escrow/history.html', context)


@login_required
def escrow_help(request):
    """Escrow help and FAQ page"""
    return render(request, 'escrow/help.html')



escrow_detail = escrow_transaction_detail
detail = escrow_transaction_detail
raise_dispute = initiate_dispute