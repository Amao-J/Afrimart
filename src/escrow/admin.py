# escrow/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import EscrowTransaction, EscrowDispute, EscrowStatusHistory
from django.utils import timezone


@admin.register(EscrowTransaction)
class EscrowTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id',
        'order_link',
        'buyer_link',
        'seller_link',
        'amount_display',
        'status_badge',
        'days_in_escrow_display',
        'created_at'
    ]
    list_filter = ['status', 'created_at', 'payment_received_at']
    search_fields = [
        'transaction_id',
        'buyer__username',
        'seller__username',
        'order__id'
    ]
    readonly_fields = [
        'transaction_id',
        'order',
        'buyer',
        'seller',
        'created_at',
        'payment_received_at',
        'shipped_at',
        'delivered_at',
        'completed_at',
        'refunded_at',
        'total_amount_display'
    ]
    
    fieldsets = (
        ('Transaction Information', {
            'fields': (
                'transaction_id',
                'order',
                'status'
            )
        }),
        ('Parties', {
            'fields': ('buyer', 'seller')
        }),
        ('Financial Details', {
            'fields': (
                'amount',
                'escrow_fee',
                'total_amount',
                'total_amount_display'
            )
        }),
        ('Payment Details', {
            'fields': (
                'payment_reference',
                'payment_provider'
            )
        }),
        ('Dates', {
            'fields': (
                'created_at',
                'payment_received_at',
                'shipped_at',
                'delivered_at',
                'completed_at',
                'refunded_at',
                'auto_release_at'
            ),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': (
                'buyer_notes',
                'seller_notes',
                'admin_notes'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'release_to_seller',
        'refund_to_buyer',
        'mark_as_disputed'
    ]
    
    def order_link(self, obj):
        url = reverse('admin:main_order_change', args=[obj.order.id])
        return format_html('<a href="{}">Order #{}</a>', url, obj.order.id)
    order_link.short_description = 'Order'
    
    def buyer_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.buyer.id])
        return format_html('<a href="{}">{}</a>', url, obj.buyer.username)
    buyer_link.short_description = 'Buyer'
    
    def seller_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.seller.id])
        return format_html('<a href="{}">{}</a>', url, obj.seller.username)
    seller_link.short_description = 'Seller'
    
    def amount_display(self, obj):
        return format_html(
            '<strong style="color:#28a745;">₦{:,.2f}</strong>',
            obj.amount
        )
    amount_display.short_description = 'Amount'
    
    def total_amount_display(self, obj):
        return f"₦{obj.total_amount:,.2f}"
    total_amount_display.short_description = 'Total with Fee'
    
    def status_badge(self, obj):
        colors = {
            'pending_payment': '#ffc107',
            'in_escrow': '#17a2b8',
            'shipped': '#007bff',
            'delivered': '#28a745',
            'completed': '#28a745',
            'disputed': '#dc3545',
            'refunded': '#6c757d',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color:{}; color:white; padding:3px 10px; border-radius:3px; font-size:11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def days_in_escrow_display(self, obj):
        days = obj.days_in_escrow()
        if obj.status in ['in_escrow', 'shipped', 'delivered']:
            return format_html(
                '<span class="badge" style="background-color: #ffc107;">{} days</span>',
                days
            )
        return f"{days} days"
    days_in_escrow_display.short_description = 'Duration'
    
    # Admin actions
    def release_to_seller(self, request, queryset):
        """Release funds to seller"""
        from main.models import Wallet, WalletTransaction
        released = 0
        
        for escrow in queryset.filter(status__in=['delivered', 'shipped']):
            try:
                # Get or create seller wallet
                seller_wallet, _ = Wallet.objects.get_or_create(user=escrow.seller)
                
                # Credit seller wallet
                seller_wallet.credit(escrow.amount)
                
                # Create wallet transaction
                WalletTransaction.objects.create(
                    wallet=seller_wallet,
                    amount=escrow.amount,
                    transaction_type='escrow_release',
                    description=f'Admin released escrow for Order #{escrow.order.id}',
                    reference=escrow.transaction_id
                )
                
                # Update escrow
                escrow.status = 'completed'
                escrow.completed_at = timezone.now()
                escrow.save()
                
                # Log status change
                EscrowStatusHistory.objects.create(
                    escrow=escrow,
                    old_status='delivered',
                    new_status='completed',
                    changed_by=request.user,
                    reason='Admin released funds to seller'
                )
                
                released += 1
            except Exception as e:
                self.message_user(request, f'Error releasing {escrow.transaction_id}: {e}', level='error')
        
        self.message_user(request, f'{released} transaction(s) released to sellers.')
    release_to_seller.short_description = 'Release funds to seller'
    
    def refund_to_buyer(self, request, queryset):
        """Refund to buyer"""
        from main.models import Wallet, WalletTransaction
        refunded = 0
        
        for escrow in queryset.filter(status__in=['in_escrow', 'shipped', 'delivered', 'disputed']):
            try:
                # Get or create buyer wallet
                buyer_wallet, _ = Wallet.objects.get_or_create(user=escrow.buyer)
                
                # Credit buyer wallet
                buyer_wallet.credit(escrow.total_amount)
                
                # Create wallet transaction
                WalletTransaction.objects.create(
                    wallet=buyer_wallet,
                    amount=escrow.total_amount,
                    transaction_type='escrow_refund',
                    description=f'Admin refunded escrow for Order #{escrow.order.id}',
                    reference=escrow.transaction_id
                )
                
                # Update escrow
                escrow.status = 'refunded'
                escrow.refunded_at = timezone.now()
                escrow.save()
                
                # Log status change
                EscrowStatusHistory.objects.create(
                    escrow=escrow,
                    old_status=escrow.status,
                    new_status='refunded',
                    changed_by=request.user,
                    reason='Admin processed refund to buyer'
                )
                
                refunded += 1
            except Exception as e:
                self.message_user(request, f'Error refunding {escrow.transaction_id}: {e}', level='error')
        
        self.message_user(request, f'{refunded} transaction(s) refunded to buyers.')
    refund_to_buyer.short_description = 'Refund to buyer'
    
    def mark_as_disputed(self, request, queryset):
        """Mark as disputed"""
        updated = queryset.filter(status__in=['in_escrow', 'shipped', 'delivered']).update(status='disputed')
        
        for escrow in queryset.filter(status__in=['in_escrow', 'shipped', 'delivered']):
            EscrowStatusHistory.objects.create(
                escrow=escrow,
                old_status=escrow.status,
                new_status='disputed',
                changed_by=request.user,
                reason='Admin marked as disputed'
            )
        
        self.message_user(request, f'{updated} transaction(s) marked as disputed.')
    mark_as_disputed.short_description = 'Mark as disputed'


@admin.register(EscrowDispute)
class EscrowDisputeAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'escrow_link',
        'raised_by_link',
        'reason',
        'status_badge',
        'days_open_display',
        'created_at'
    ]
    list_filter = ['status', 'reason', 'created_at']
    search_fields = [
        'escrow__transaction_id',
        'raised_by__username'
    ]
    readonly_fields = [
        'escrow',
        'raised_by',
        'created_at',
        'updated_at',
        'resolved_at'
    ]
    
    fieldsets = (
        ('Dispute Information', {
            'fields': (
                'escrow',
                'reason',
                'buyer_evidence',
                'seller_evidence',
                'raised_by'
            )
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Resolution', {
            'fields': (
                'resolved_by',
                'resolution_notes'
            )
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['resolve_for_buyer', 'resolve_for_seller']
    
    def escrow_link(self, obj):
        url = reverse('admin:escrow_escrowtransaction_change', args=[obj.escrow.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.escrow.transaction_id
        )
    escrow_link.short_description = 'Escrow Transaction'
    
    def raised_by_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.raised_by.id])
        return format_html('<a href="{}">{}</a>', url, obj.raised_by.username)
    raised_by_link.short_description = 'Raised By'
    
    def status_badge(self, obj):
        colors = {
            'open': '#ffc107',
            'under_review': '#17a2b8',
            'resolved_buyer': '#28a745',
            'resolved_seller': '#007bff',
            'closed': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color:{}; color:white; padding:3px 10px; border-radius:3px; font-size:11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def days_open_display(self, obj):
        days = obj.days_open()
        if obj.status in ['open', 'under_review']:
            return format_html(
                '<span class="badge" style="background-color: #dc3545;">{} days</span>',
                days
            )
        return f"{days} days"
    days_open_display.short_description = 'Duration'
    
    # Admin actions
    def resolve_for_buyer(self, request, queryset):
        """Resolve in favor of buyer (refund)"""
        from main.models import Wallet, WalletTransaction
        resolved = 0
        
        for dispute in queryset.filter(status__in=['open', 'under_review']):
            escrow = dispute.escrow
            
            try:
                # Refund to buyer
                buyer_wallet, _ = Wallet.objects.get_or_create(user=escrow.buyer)
                buyer_wallet.credit(escrow.total_amount)
                
                WalletTransaction.objects.create(
                    wallet=buyer_wallet,
                    amount=escrow.total_amount,
                    transaction_type='escrow_refund',
                    description=f'Dispute resolved in buyer favor for Order #{escrow.order.id}',
                    reference=escrow.transaction_id
                )
                
                # Update escrow
                escrow.status = 'refunded'
                escrow.refunded_at = timezone.now()
                escrow.save()
                
                # Update dispute
                dispute.status = 'resolved_buyer'
                dispute.resolved_by = request.user
                dispute.resolved_at = timezone.now()
                dispute.save()
                
                # Log
                EscrowStatusHistory.objects.create(
                    escrow=escrow,
                    old_status='disputed',
                    new_status='refunded',
                    changed_by=request.user,
                    reason='Dispute resolved in buyer favor'
                )
                
                resolved += 1
            except Exception as e:
                self.message_user(request, f'Error resolving dispute {dispute.id}: {e}', level='error')
        
        self.message_user(request, f'{resolved} dispute(s) resolved in favor of buyer.')
    resolve_for_buyer.short_description = 'Resolve for buyer (refund)'
    
    def resolve_for_seller(self, request, queryset):
        """Resolve in favor of seller (release)"""
        from main.models import Wallet, WalletTransaction
        resolved = 0
        
        for dispute in queryset.filter(status__in=['open', 'under_review']):
            escrow = dispute.escrow
            
            try:
                # Release to seller
                seller_wallet, _ = Wallet.objects.get_or_create(user=escrow.seller)
                seller_wallet.credit(escrow.amount)
                
                WalletTransaction.objects.create(
                    wallet=seller_wallet,
                    amount=escrow.amount,
                    transaction_type='escrow_release',
                    description=f'Dispute resolved in seller favor for Order #{escrow.order.id}',
                    reference=escrow.transaction_id
                )
                
                # Update escrow
                escrow.status = 'completed'
                escrow.completed_at = timezone.now()
                escrow.save()
                
                # Update dispute
                dispute.status = 'resolved_seller'
                dispute.resolved_by = request.user
                dispute.resolved_at = timezone.now()
                dispute.save()
                
                # Log
                EscrowStatusHistory.objects.create(
                    escrow=escrow,
                    old_status='disputed',
                    new_status='completed',
                    changed_by=request.user,
                    reason='Dispute resolved in seller favor'
                )
                
                resolved += 1
            except Exception as e:
                self.message_user(request, f'Error resolving dispute {dispute.id}: {e}', level='error')
        
        self.message_user(request, f'{resolved} dispute(s) resolved in favor of seller.')
    resolve_for_seller.short_description = 'Resolve for seller (release)'


@admin.register(EscrowStatusHistory)
class EscrowStatusHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'escrow_link',
        'old_status',
        'new_status',
        'changed_by_link',
        'created_at'
    ]
    list_filter = ['new_status', 'created_at']
    search_fields = ['escrow__transaction_id', 'reason']
    readonly_fields = ['escrow', 'old_status', 'new_status', 'changed_by', 'reason', 'created_at']
    
    def escrow_link(self, obj):
        url = reverse('admin:escrow_escrowtransaction_change', args=[obj.escrow.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.escrow.transaction_id
        )
    escrow_link.short_description = 'Escrow'
    
    def changed_by_link(self, obj):
        if obj.changed_by:
            url = reverse('admin:auth_user_change', args=[obj.changed_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.changed_by.username)
        return "System"
    changed_by_link.short_description = 'Changed By'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False