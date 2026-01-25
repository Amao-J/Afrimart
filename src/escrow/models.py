from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# Import from main app
from main.models import Order


class EscrowTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending_payment', 'Pending Payment'),
        ('in_escrow', 'In Escrow'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('disputed', 'Disputed'),
        ('cancelled', 'Cancelled'),
    ]
    
    transaction_id = models.CharField(max_length=50, unique=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='escrow')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='escrow_purchases')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='escrow_sales')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    escrow_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_payment')
    
    # Payment details
    payment_provider = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=200, blank=True)
    payment_received_at = models.DateTimeField(null=True, blank=True)
    
    # Shipping details
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Auto-release
    auto_release_days = models.IntegerField(default=7)
    auto_release_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_id} - {self.get_status_display()}"
    
    def calculate_auto_release_date(self):
        """Calculate when funds should be auto-released"""
        if self.delivered_at:
            self.auto_release_at = self.delivered_at + timedelta(days=self.auto_release_days)
            self.save()
    
    def can_buyer_confirm(self):
        """Check if buyer can confirm delivery"""
        return self.status == 'shipped'
    
    def can_release_to_seller(self):
        """Check if funds can be released to seller"""
        return self.status == 'delivered'


class EscrowDispute(models.Model):
    DISPUTE_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('resolved_buyer', 'Resolved - Buyer Wins'),
        ('resolved_seller', 'Resolved - Seller Wins'),
        ('resolved_split', 'Resolved - Split Decision'),
    ]
    
    escrow = models.OneToOneField(EscrowTransaction, on_delete=models.CASCADE, related_name='dispute')
    raised_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disputes_raised')
    reason = models.TextField()
    
    buyer_evidence = models.TextField(blank=True)
    seller_evidence = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=DISPUTE_STATUS_CHOICES, default='pending')
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='disputes_resolved'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Dispute for {self.escrow.transaction_id}"


class EscrowStatusHistory(models.Model):
    escrow = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.escrow.transaction_id}: {self.old_status} → {self.new_status}"