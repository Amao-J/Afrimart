from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver



NIGERIAN_BANKS = [
    ('044', 'Access Bank'),
    ('063', 'Access Bank (Diamond)'),
    ('035A', 'ALAT by WEMA'),
    ('401', 'ASO Savings and Loans'),
    ('MFB', 'Bowen Microfinance Bank'),
    ('50931', 'Eyowo'),
    ('070', 'Fidelity Bank'),
    ('011', 'First Bank of Nigeria'),
    ('214', 'First City Monument Bank'),
    ('058', 'Guaranty Trust Bank'),
    ('030', 'Heritage Bank'),
    ('301', 'Jaiz Bank'),
    ('082', 'Keystone Bank'),
    ('50211', 'Kuda Bank'),
    ('090267', 'Mint-Finex MICROFINANCE BANK'),
    ('090175', 'Rubies Microfinance Bank'),
    ('101', 'Providus Bank'),
    ('076', 'Polaris Bank'),
    ('221', 'Stanbic IBTC Bank'),
    ('068', 'Standard Chartered Bank'),
    ('232', 'Sterling Bank'),
    ('100', 'Suntrust Bank'),
    ('032', 'Union Bank of Nigeria'),
    ('033', 'United Bank For Africa'),
    ('215', 'Unity Bank'),
    ('035', 'Wema Bank'),
    ('057', 'Zenith Bank'),
]

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products', null=True, blank=True)  
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0) 
    is_featured = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    is_deal_of_the_day = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
       
    def get_discounted_price(self):
        """Calculate price after discount"""
        if self.discount_percentage > 0:
            discount_amount = self.price * (self.discount_percentage / 100)
            return self.price - discount_amount
        return self.price
    
    def get_savings(self):
        """Calculate how much user saves"""
        if self.discount_percentage > 0:
            return self.price - self.get_discounted_price()
        return 0
    
    @property
    def has_discount(self):
        """Check if product has discount"""
        return self.discount_percentage > 0
    
    def get_primary_image(self):
        image = (
            self.images.filter(is_primary=True).first()
            or self.images.first()
        )
        if not image:
            return None

        return image.cloudinary_url or image.image.url
        
    def get_all_images(self):
            
        return self.images.all().order_by('-is_primary', 'order')


class ProductImage(models.Model):
    """Model to handle multiple images for a single product"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    cloudinary_url = models.URLField(max_length=500, blank=True)  
    is_primary = models.BooleanField(default=False, help_text="Set as the main product image")
    order = models.PositiveIntegerField(default=0, help_text="Order of display")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', 'order']
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
    
    def __str__(self):
        return f"{self.product.name} - Image {self.order}"


class BankAccount(models.Model):
    """Bank account details for sellers to receive payments"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bank_account')
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=10, help_text="Flutterwave bank code")
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bank Account'
        verbose_name_plural = 'Bank Accounts'
    
    def __str__(self):
        return f"{self.user.username} - {self.bank_name} ({self.account_number})"
    
    def verify_account(self):
        """
        Verify bank account details with Flutterwave
        Returns: dict with success status and account name if successful
        """
        from django.conf import settings
        import requests
        
        url = "https://api.flutterwave.com/v3/accounts/resolve"
        
        headers = {
            'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "account_number": self.account_number,
            "account_bank": self.bank_code
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            data = response.json()
            
            if data.get('status') == 'success':
                account_name = data['data']['account_name']
                
                
                self.account_name = account_name
                self.is_verified = True
                self.verified_at = timezone.now()
                self.save()
                
                return {
                    'success': True,
                    'account_name': account_name,
                    'message': 'Account verified successfully'
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', 'Verification failed')
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'Verification error: {str(e)}'
            }




class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    FLUTTERWAVE_CURRENCIES = (
        ("NGN", "Nigerian Naira"),
        ("USD", "US Dollar"),
        ("GHS", "Ghana Cedi"),
        ("KES", "Kenyan Shilling"),
        ("ZAR", "South African Rand"),
        ("EUR", "Euro"),
        ("GBP", "British Pound"),
    )
    
    currency = models.CharField(
        max_length=3,
        choices=FLUTTERWAVE_CURRENCIES,
        default="NGN"
    )
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales')
    
    # Order details
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount_usd = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    fx_rate = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    
    # Payment details
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=200, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Shipping
    tracking_number = models.CharField(max_length=100, blank=True)
    shipping_address = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} - {self.buyer.username}"
    
    def can_be_paid(self):
        """Check if order can be paid"""
        return self.payment_status in ['pending', 'failed']
    
    def get_total_items(self):
        """Get total number of items"""
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def get_total(self):
        return self.quantity * self.price
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Wallet - {self.balance}"
    
    def can_debit(self, amount):
        return self.balance >= Decimal(str(amount))
    
    def credit(self, amount):
        """Add money to wallet"""
        self.balance += Decimal(str(amount))
        self.save()
    
    def debit(self, amount):
        """Remove money from wallet"""
        if self.can_debit(amount):
            self.balance -= Decimal(str(amount))
            self.save()
            return True
        return False
    
class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  
    transaction_type = models.CharField(max_length=20)  
    description = models.TextField()
    reference = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CurrencyRate(models.Model):
    base = models.CharField(max_length=3, default="USD")
    quote = models.CharField(max_length=3)  # NGN, GHS, KES
    rate = models.DecimalField(max_digits=12, decimal_places=6)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("base", "quote")

    def __str__(self):
        return f"1 {self.base} = {self.rate} {self.quote}"


class Payment(models.Model):
    """Track all normal payments"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('flutterwave', 'Flutterwave'),
        ('paystack', 'Paystack'),
        ('bank_transfer', 'Bank Transfer'),
        ('wallet', 'Wallet'),
        ('cash', 'Cash on Delivery'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_usd = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    fx_rate = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default='NGN')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference = models.CharField(max_length=200, unique=True)
    
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_type = models.CharField(max_length=20, default='normal')  # 'normal' or 'escrow'
    transaction_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    metadata = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Payment {self.reference} - {self.status}"
    
    def mark_as_successful(self):
        """Mark payment as successful"""
        self.status = 'successful'
        self.completed_at = timezone.now()
        self.save()
    
    def get_status_badge_class(self):
        """Return Bootstrap badge class for status"""
        status_classes = {
            'pending': 'warning',
            'successful': 'success',
            'failed': 'danger',
            'cancelled': 'secondary',
            'refunded': 'info',
        }
        return status_classes.get(self.status, 'secondary')


class Refund(models.Model):
    """Handle payment refunds"""
    REFUND_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    REFUND_REASON_CHOICES = [
        ('buyer_request', 'Buyer Request'),
        ('order_cancelled', 'Order Cancelled'),
        ('product_unavailable', 'Product Unavailable'),
        ('dispute_resolved', 'Dispute Resolved'),
        ('duplicate_payment', 'Duplicate Payment'),
        ('other', 'Other'),
    ]
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refunds')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=50, choices=REFUND_REASON_CHOICES)
    reason_details = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='pending')
    refund_reference = models.CharField(max_length=200, unique=True)
    
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_refunds'
    )
    admin_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Refund {self.refund_reference} - {self.status}"


class UserProfile(models.Model):
    """Extended user profile with phone and address"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Contact information
    phone = models.CharField(max_length=20, blank=True)
    
    # Address
    street_address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Nigeria')
    
    # Additional
    date_of_birth = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    # Seller Information
    is_seller = models.BooleanField(default=False, help_text="User is a seller/vendor")
    seller_approved = models.BooleanField(default=False, help_text="Seller account is approved")
    seller_application_date = models.DateTimeField(null=True, blank=True)
    seller_approval_date = models.DateTimeField(null=True, blank=True)
    seller_description = models.TextField(blank=True, help_text="Seller business description")
    seller_store_name = models.CharField(max_length=255, blank=True, help_text="Store name for sellers")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_full_address(self):
        """Return formatted full address"""
        parts = [self.street_address, self.city, self.state, self.country]
        return ', '.join(filter(None, parts))
    
    def get_display_phone(self):
        """Return formatted phone number"""
        if not self.phone:
            return 'Not provided'
        
      
        phone = self.phone.replace('+', '').replace(' ', '').replace('-', '')
        
        
        if phone.startswith('234') and len(phone) == 13:
            phone = phone[3:]  # Remove 234
            return f"+234 {phone[:3]} {phone[3:6]} {phone[6:]}"
        
        
        if len(phone) >= 10:
            return f"+{phone[:3]} {phone[3:6]} {phone[6:]}"
        
        return self.phone


class WishlistItem(models.Model):
   
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

# Signal handlers
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created"""
    if created:
        UserProfile.objects.get_or_create(user=instance)




@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()

