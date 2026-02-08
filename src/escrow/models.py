# escrow/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from main.models import Order
from decimal import Decimal
from datetime import timedelta


class EscrowTransaction(models.Model):
    """Escrow transactions that hold payment until buyer confirms delivery"""
    
    STATUS_CHOICES = [
        ('pending_payment', 'Pending Payment'),
        ('in_escrow', 'In Escrow'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('disputed', 'Disputed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Transaction identifiers
    transaction_id = models.CharField(max_length=100, unique=True, db_index=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='escrow')
    
    # Parties involved
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='escrow_purchases')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='escrow_sales')
    
    # Financial details
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Order amount")
    escrow_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="2.5% escrow fee")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Amount + escrow fee")
    
    # Payment details
    payment_reference = models.CharField(max_length=200, blank=True, help_text="Flutterwave transaction ID")
    payment_provider = models.CharField(max_length=50, blank=True, default='flutterwave')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_payment', db_index=True)
    
    # Important dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_received_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    
    # Auto-release configuration
    auto_release_at = models.DateTimeField(null=True, blank=True, help_text="Auto-release date (14 days after delivery)")
    auto_release_days = models.IntegerField(default=14, help_text="Days until auto-release after delivery")
    
    # Notes
    buyer_notes = models.TextField(blank=True)
    seller_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['buyer', '-created_at']),
            models.Index(fields=['seller', '-created_at']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Escrow Transaction'
        verbose_name_plural = 'Escrow Transactions'
    
    def __str__(self):
        return f"{self.transaction_id} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate fees if not set
        if not self.escrow_fee:
            self.escrow_fee = (self.amount * Decimal('0.025')).quantize(Decimal('0.01'))
        if not self.total_amount:
            self.total_amount = self.amount + self.escrow_fee
        super().save(*args, **kwargs)
    
    def calculate_auto_release_date(self):
        """Calculate when funds should be auto-released"""
        if self.delivered_at and not self.auto_release_at:
            self.auto_release_at = self.delivered_at + timedelta(days=self.auto_release_days)
            self.save(update_fields=['auto_release_at'])
    
    def days_in_escrow(self):
        """Calculate days money has been held"""
        if self.payment_received_at:
            if self.completed_at:
                return (self.completed_at - self.payment_received_at).days
            return (timezone.now() - self.payment_received_at).days
        return 0
    
    def days_until_auto_release(self):
        """Days until auto-release"""
        if self.auto_release_at:
            days = (self.auto_release_at - timezone.now()).days
            return max(0, days)
        return None
    
    def can_buyer_confirm(self):
        """Check if buyer can confirm delivery"""
        return self.status == 'shipped'
    
    def can_release_to_seller(self):
        """Check if funds can be released to seller"""
        return self.status in ['delivered', 'shipped']
    
    def can_be_disputed(self):
        """Check if transaction can be disputed"""
        return self.status in ['shipped', 'delivered', 'in_escrow']
    
    def release_funds_to_seller(self):
        """Release funds to seller's wallet"""
        if not self.can_release_to_seller():
            return False
        
        from main.models import Wallet, WalletTransaction
        
        try:
            # Get or create seller wallet
            seller_wallet, _ = Wallet.objects.get_or_create(user=self.seller)
            
            # Credit seller wallet
            seller_wallet.credit(self.amount)
            
            # Create wallet transaction record
            WalletTransaction.objects.create(
                wallet=seller_wallet,
                amount=self.amount,
                transaction_type='escrow_release',
                description=f'Escrow payment released for Order #{self.order.id}',
                reference=self.transaction_id
            )
            
            # Update status
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
            
            # Update order
            self.order.payment_status = 'paid'
            self.order.status = 'delivered'
            self.order.save()
            
            return True
        except Exception as e:
            print(f"Error releasing funds: {e}")
            return False
    
    def refund_to_buyer(self):
        """Refund money back to buyer's wallet"""
        if self.status == 'completed':
            return False
        
        from main.models import Wallet, WalletTransaction
        
        try:
            # Get or create buyer wallet
            buyer_wallet, _ = Wallet.objects.get_or_create(user=self.buyer)
            
            # Credit buyer wallet (full amount including escrow fee)
            buyer_wallet.credit(self.total_amount)
            
            # Create wallet transaction record
            WalletTransaction.objects.create(
                wallet=buyer_wallet,
                amount=self.total_amount,
                transaction_type='escrow_refund',
                description=f'Escrow refund for Order #{self.order.id}',
                reference=self.transaction_id
            )
            
            # Update status
            self.status = 'refunded'
            self.refunded_at = timezone.now()
            self.save()
            
            # Update order
            self.order.payment_status = 'refunded'
            self.order.status = 'cancelled'
            self.order.save()
            
            return True
        except Exception as e:
            print(f"Error refunding: {e}")
            return False


class EscrowDispute(models.Model):
    """Disputes raised on escrow transactions"""
    
    DISPUTE_REASON_CHOICES = [
        ('not_received', 'Item Not Received'),
        ('wrong_item', 'Wrong Item Delivered'),
        ('damaged', 'Item Damaged'),
        ('not_as_described', 'Not as Described'),
        ('counterfeit', 'Counterfeit/Fake Product'),
        ('defective', 'Defective Product'),
        ('other', 'Other Reason'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved_buyer', 'Resolved - Buyer Favor'),
        ('resolved_seller', 'Resolved - Seller Favor'),
        ('closed', 'Closed'),
    ]
    
    escrow = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE, related_name='disputes')
    
    # Who raised it
    raised_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disputes_raised')
    
    # Dispute details
    reason = models.CharField(max_length=50, choices=DISPUTE_REASON_CHOICES)
    buyer_evidence = models.TextField(blank=True, help_text="Buyer's evidence")
    seller_evidence = models.TextField(blank=True, help_text="Seller's evidence")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Resolution
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disputes_resolved'
    )
    resolution_notes = models.TextField(blank=True)
    resolution_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount to refund/release"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Escrow Dispute'
        verbose_name_plural = 'Escrow Disputes'
    
    def __str__(self):
        return f"Dispute for {self.escrow.transaction_id} - {self.get_status_display()}"
    
    def days_open(self):
        """Calculate days dispute has been open"""
        if self.resolved_at:
            return (self.resolved_at - self.created_at).days
        return (timezone.now() - self.created_at).days


class EscrowStatusHistory(models.Model):
    """Track status changes for escrow transactions"""
    
    escrow = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Escrow Status History'
        verbose_name_plural = 'Escrow Status Histories'
    
    def __str__(self):
        return f"{self.escrow.transaction_id}: {self.old_status} → {self.new_status}"