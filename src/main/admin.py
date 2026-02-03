from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Product, Order, OrderItem, Wallet, WalletTransaction, Payment, Refund, ProductImage, UserProfile
from decimal import Decimal
import uuid
from django.utils import timezone


class ProductImageInline(admin.TabularInline):
    """Inline editor for product images"""
    model = ProductImage
    extra = 1
    fields = ['image', 'is_primary', 'order', 'preview_image']
    readonly_fields = ['preview_image', 'uploaded_at']
    
    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" style="max-height:100px; object-fit:cover;" />', obj.image.url)
        return "No image"
    preview_image.short_description = 'Preview'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'display_image', 'is_primary', 'order', 'uploaded_at']
    list_filter = ['is_primary', 'uploaded_at', 'product']
    search_fields = ['product__name']
    readonly_fields = ['uploaded_at', 'preview_image']
    
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;" />', obj.image.url)
        return "No image"
    display_image.short_description = 'Thumbnail'
    
    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="300" />', obj.image.url)
        return "No image"
    preview_image.short_description = 'Full Preview'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock', 'seller', 'images_count', 'is_featured', 'is_deal_of_the_day', 'is_trending', 'created_at', 'display_image']
    list_filter = ['created_at', 'stock', 'is_featured', 'is_deal_of_the_day', 'is_trending', 'seller']
    search_fields = ['name', 'description', 'seller__username']
    
    # Must include any methods used in fieldsets here
    readonly_fields = ['created_at', 'updated_at', 'preview_image']
    inlines = [ProductImageInline]
    
    # Define fieldsets directly instead of using get_fieldsets
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'description', 'category', 'seller', 'price', 'stock', 'discount_percentage')
        }),
        ('Promotions & Status', {
            'fields': ('is_featured', 'is_trending', 'is_deal_of_the_day'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # --- Utility Methods ---
    def display_image(self, obj):
        primary_img = obj.get_primary_image()
        if primary_img:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;" />', primary_img)
        return "No image"
    display_image.short_description = 'Image'
    
    def images_count(self, obj):
        count = obj.images.count()
        return format_html('<span class="badge" style="background-color: #417690;">{}</span>', count)
    images_count.short_description = 'Images'
    
    def preview_image(self, obj):
        primary_img = obj.get_primary_image()
        if primary_img:
            return format_html('<img src="{}" width="200" />', primary_img)
        return "No image uploaded"
    preview_image.short_description = 'Preview'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'get_total']
    can_delete = False
    
    def get_total(self, obj):
        return f"₦{obj.get_total():,.2f}"
    get_total.short_description = 'Total'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'buyer_link', 
        'seller_link', 
        'total_amount_display', 
        'status_badge', 
        'payment_status_badge',
        'created_at'
    ]
    list_filter = ['status', 'payment_status', 'created_at', 'paid_at']
    search_fields = ['id', 'buyer__username', 'buyer__email', 'seller__username', 'tracking_number']
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'paid_at',
        'total_amount_display',
        'buyer_link',
        'seller_link'
    ]
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('buyer_link', 'seller_link', 'total_amount', 'total_amount_display', 'status')
        }),
        ('Payment Information', {
            'fields': ('payment_status', 'payment_method', 'payment_reference', 'paid_at')
        }),
        ('Shipping Information', {
            'fields': ('shipping_address', 'tracking_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_paid']
    
    def buyer_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.buyer.id])
        return format_html('<a href="{}">{}</a>', url, obj.buyer.get_full_name() or obj.buyer.username)
    buyer_link.short_description = 'Buyer'
    
    def seller_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.seller.id])
        return format_html('<a href="{}">{}</a>', url, obj.seller.get_full_name() or obj.seller.username)
    seller_link.short_description = 'Seller'
    
    def total_amount_display(self, obj):
        return f"₦{obj.total_amount:,.2f}"
    total_amount_display.short_description = 'Total Amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'shipped': '#007bff',
            'delivered': '#28a745',
            'cancelled': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color:{}; color:white; padding:3px 10px; border-radius:3px; font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def payment_status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'paid': '#28a745',
            'failed': '#dc3545',
            'refunded': '#17a2b8',
        }
        color = colors.get(obj.payment_status, '#6c757d')
        return format_html(
            '<span style="background-color:{}; color:white; padding:3px 10px; border-radius:3px; font-size:11px;">{}</span>',
            color, obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment'
    
    # Admin actions
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(status='processing')
        self.message_user(request, f'{updated} order(s) marked as processing.')
    mark_as_processing.short_description = 'Mark selected orders as Processing'
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(status='shipped')
        self.message_user(request, f'{updated} order(s) marked as shipped.')
    mark_as_shipped.short_description = 'Mark selected orders as Shipped'
    
    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(status='delivered')
        self.message_user(request, f'{updated} order(s) marked as delivered.')
    mark_as_delivered.short_description = 'Mark selected orders as Delivered'
    
    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(payment_status='pending').update(
            payment_status='paid',
            paid_at=timezone.now()
        )
        self.message_user(request, f'{updated} order(s) marked as paid.')
    mark_as_paid.short_description = 'Mark selected orders as Paid'


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'balance_display', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['user', 'created_at', 'updated_at', 'balance_display']
    actions = ['seed_selected_wallets']
    
    fieldsets = (
        ('Wallet Information', {
            'fields': ('user', 'balance', 'balance_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name() or obj.user.username)
    user_link.short_description = 'User'
    
    def balance_display(self, obj):
        return format_html(
            '<strong style="color:#28a745; font-size:14px;">₦{:,.2f}</strong>',
            obj.balance
        )
    balance_display.short_description = 'Balance'
    
    def has_add_permission(self, request):
        # Prevent manual wallet creation - should be auto-created
        return False

    def seed_selected_wallets(self, request, queryset):
        """Seed selected wallets with a fixed amount (admin action)"""
        amount = Decimal('100000')  # ₦100,000 default seed amount
        seeded = 0
        for wallet in queryset:
            try:
                wallet.credit(amount)
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=amount,
                    transaction_type='seed',
                    description='Admin seed',
                    reference=f'ADMINSEED-{uuid.uuid4().hex[:8].upper()}'
                )
                seeded += 1
            except Exception:
                continue
        self.message_user(request, f'Seeded {seeded} wallet(s) with ₦{amount:,.0f}')
    seed_selected_wallets.short_description = 'Seed selected wallets with ₦100,000'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'reference_short',
        'user_link',
        'order_link',
        'amount_display',
        'payment_method',
        'status_badge',
        'created_at'
    ]
    list_filter = ['status', 'payment_method', 'payment_type', 'created_at']
    search_fields = ['reference', 'user__username', 'user__email', 'order__id']
    readonly_fields = [
        'order', 
        'user', 
        'reference', 
        'created_at', 
        'updated_at', 
        'completed_at',
        'metadata_display'
    ]
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('order', 'user', 'reference', 'amount', 'currency', 'payment_method')
        }),
        ('Status', {
            'fields': ('status', 'payment_type', 'transaction_fee')
        }),
        ('Metadata', {
            'fields': ('metadata_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_successful', 'mark_as_failed']
    
    def reference_short(self, obj):
        return f"{obj.reference[:20]}..." if len(obj.reference) > 20 else obj.reference
    reference_short.short_description = 'Reference'
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    
    def order_link(self, obj):
        url = reverse('admin:main_order_change', args=[obj.order.id])
        return format_html('<a href="{}">Order #{}</a>', url, obj.order.id)
    order_link.short_description = 'Order'
    
    def amount_display(self, obj):
        return f"₦{obj.amount:,.2f}"
    amount_display.short_description = 'Amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'successful': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
            'refunded': '#17a2b8',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color:{}; color:white; padding:3px 10px; border-radius:3px; font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def metadata_display(self, obj):
        if obj.metadata:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.metadata, indent=2))
        return "No metadata"
    metadata_display.short_description = 'Metadata'
    
    # Admin actions
    def mark_as_successful(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='successful', completed_at=timezone.now())
        self.message_user(request, f'{updated} payment(s) marked as successful.')
    mark_as_successful.short_description = 'Mark selected as Successful'
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.update(status='failed')
        self.message_user(request, f'{updated} payment(s) marked as failed.')
    mark_as_failed.short_description = 'Mark selected as Failed'


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = [
        'refund_reference',
        'user_link',
        'order_link',
        'amount_display',
        'reason',
        'status_badge',
        'created_at'
    ]
    list_filter = ['status', 'reason', 'created_at']
    search_fields = ['refund_reference', 'user__username', 'order__id']
    readonly_fields = ['payment', 'order', 'user', 'refund_reference', 'created_at', 'processed_at']
    
    fieldsets = (
        ('Refund Information', {
            'fields': ('payment', 'order', 'user', 'refund_reference', 'amount')
        }),
        ('Reason', {
            'fields': ('reason', 'reason_details')
        }),
        ('Status & Review', {
            'fields': ('status', 'reviewed_by', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_refunds', 'reject_refunds']
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    
    def order_link(self, obj):
        url = reverse('admin:main_order_change', args=[obj.order.id])
        return format_html('<a href="{}">Order #{}</a>', url, obj.order.id)
    order_link.short_description = 'Order'
    
    def amount_display(self, obj):
        return f"₦{obj.amount:,.2f}"
    amount_display.short_description = 'Amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color:{}; color:white; padding:3px 10px; border-radius:3px; font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    # Admin actions
    def approve_refunds(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='completed',
            reviewed_by=request.user,
            processed_at=timezone.now()
        )
        self.message_user(request, f'{updated} refund(s) approved.')
    approve_refunds.short_description = 'Approve selected refunds'
    
    def reject_refunds(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='failed',
            reviewed_by=request.user,
            processed_at=timezone.now()
        )
        self.message_user(request, f'{updated} refund(s) rejected.')
    reject_refunds.short_description = 'Reject selected refunds'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin for managing user profiles and seller approvals"""
    list_display = ['user', 'phone', 'is_seller', 'seller_status_badge', 'seller_store_name', 'seller_application_date']
    list_filter = ['is_seller', 'seller_approved', 'seller_application_date']
    search_fields = ['user__username', 'user__email', 'seller_store_name', 'phone']
    readonly_fields = ['seller_application_date', 'seller_approval_date', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'phone', 'created_at', 'updated_at')
        }),
        ('Address', {
            'fields': ('street_address', 'city', 'state', 'country'),
            'classes': ('collapse',)
        }),
        ('Additional', {
            'fields': ('date_of_birth', 'avatar'),
            'classes': ('collapse',)
        }),
        ('Seller Account', {
            'fields': (
                'is_seller',
                'seller_approved',
                'seller_store_name',
                'seller_description',
                'seller_application_date',
                'seller_approval_date'
            )
        }),
    )
    
    def seller_status_badge(self, obj):
        """Display seller status as a badge"""
        if not obj.is_seller:
            return format_html(
                '<span class="badge" style="background-color: #ccc;">Not a Seller</span>'
            )
        elif obj.seller_approved:
            return format_html(
                '<span class="badge" style="background-color: #28a745;">Approved</span>'
            )
        else:
            return format_html(
                '<span class="badge" style="background-color: #ffc107;">Pending</span>'
            )
    seller_status_badge.short_description = 'Seller Status'
    
    actions = ['approve_sellers', 'reject_sellers']
    
    def approve_sellers(self, request, queryset):
        """Approve selected seller applications"""
        updated = queryset.filter(is_seller=True, seller_approved=False).update(
            seller_approved=True,
            seller_approval_date=timezone.now()
        )
        self.message_user(request, f'{updated} seller(s) approved!')
    approve_sellers.short_description = 'Approve selected seller applications'
    
    def reject_sellers(self, request, queryset):
        """Reject seller applications"""
        updated = queryset.filter(is_seller=True, seller_approved=False).update(
            is_seller=False
        )
        self.message_user(request, f'{updated} seller application(s) rejected.')
    reject_sellers.short_description = 'Reject selected seller applications'


# Customize admin site header
admin.site.site_header = "Techfy-NG Admin"
admin.site.site_title = "Techfy-NG Admin Portal"
admin.site.index_title = "Welcome to Techfy-NG Administration"