# main/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .utils.currency import set_user_currency, SUPPORTED_CURRENCIES, get_exchange_rate, batch_update_rates
from .models import Order, OrderItem, Product, Wallet, Payment
from decimal import Decimal
from .cart import get_cart, save_cart, get_cart_items,cart_view,update_cart,remove_from_cart,clear_cart
import uuid
import requests
import json
from django.db.models import Q
from main.utils.currency import convert_currency, get_user_currency,set_user_currency,convert_price_to_user_currency


def home(request):
    """Home page with featured products and discount handling"""
    # Get featured products or latest 12 products
    products = Product.objects.filter(is_featured=True).order_by('-created_at')[:12]
    
    # If no featured products, get latest products
    if not products.exists():
        products = Product.objects.filter(stock__gt=0).order_by('-created_at')[:12]
    
    # Convert prices to user's currency and handle discounts
    for product in products:
        # Use discounted price if available
        price_to_convert = product.get_discounted_price()
        
        price_info = convert_price_to_user_currency(
            price_to_convert,
            'NGN',
            request
        )
        product.converted_price = price_info['formatted']
        
        # If product has discount, also convert original price and savings
        if product.has_discount:
            # Convert original price
            original_price_info = convert_price_to_user_currency(
                product.price,
                'NGN',
                request
            )
            product.converted_original_price = original_price_info['formatted']
            
            # Convert savings amount
            savings_info = convert_price_to_user_currency(
                product.get_savings(),
                'NGN',
                request
            )
            product.converted_savings = savings_info['formatted']
    
    # Get all categories
    from .models import Category
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'total_products': Product.objects.count(),
        'supported_currencies': SUPPORTED_CURRENCIES,
        'user_currency': get_user_currency(request)
    }
    return render(request, 'main/home.html', context)


def product_list(request):
    """List all products with search and filter"""
    products = Product.objects.filter(stock__gt=0)

    for product in products:
        price_info = convert_price_to_user_currency(
            product.price, 
            'NGN',  # Original currency
            request
        )
        product.converted_price = price_info['formatted']
    
    
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Sort
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    else:
        products = products.order_by('-created_at')
    
    context = {
        'products': products,
        'search_query': search_query,
        'sort_by': sort_by
    }
    return render(request, 'main/product_list.html', context)


def product_detail(request, product_id):
    """Product detail page"""
    product = get_object_or_404(Product, id=product_id)
    
    # Get related products (same category or random)
    related_products = Product.objects.filter(
        stock__gt=0
    ).exclude(id=product_id).order_by('?')[:4]
    
    context = {
        'product': product,
        'related_products': related_products
    }
    return render(request, 'main/product_detail.html', context)

def add_to_cart(request, product_id):
    """Add a product to the cart"""
    product = get_object_or_404(Product, id=product_id)
    
    if product.stock <= 0:
        messages.error(request, 'Product is out of stock')
        return redirect('product_detail', product_id=product.id)
    
    cart = get_cart(request)
    product_id_str = str(product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    current_quantity = cart.get(product_id_str, 0)
    new_quantity = current_quantity + quantity
    
    if new_quantity > product.stock:
        messages.error(request, f'Only {product.stock} units available')
        return redirect('product_detail', product_id=product.id)
    
    cart[product_id_str] = new_quantity
    save_cart(request, cart)
    
    messages.success(request, f'Added {quantity} x {product.name} to cart')
    return redirect('cart')

@login_required
def dashboard(request):
    """User dashboard"""
    # Get user's orders
    orders = Order.objects.filter(buyer=request.user).order_by('-created_at')[:5]
    
    # Get user's wallet
    from .models import Wallet
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    context = {
        'recent_orders': orders,
        'wallet': wallet,
        'total_orders': Order.objects.filter(buyer=request.user).count(),
        'pending_orders': Order.objects.filter(buyer=request.user, payment_status='pending').count()
    }
    return render(request, 'main/dashboard.html', context)


@login_required
def wallet_view(request):
    """User wallet view"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Convert balance to user's currency
    balance_info = convert_price_to_user_currency(
        wallet.balance,
        'NGN',
        request
    )
    
    context = {
        'wallet': wallet,
        'wallet_balance': balance_info['formatted'],
        'wallet_amount': balance_info['amount'],
    }
    
    return render(request, 'main/wallet.html', context)


@login_required
def checkout(request):
    """Checkout process"""
    cart_data = get_cart_items(request)
    
    # Check if cart is empty
    if not cart_data['items']:
        messages.warning(request, "Your cart is empty")
        return redirect('cart')
    
    # Check stock availability for all items
    for item in cart_data['items']:
        if item['quantity'] > item['product'].stock:
            messages.error(request, f"{item['product'].name} only has {item['product'].stock} units in stock")
            return redirect('cart')
    
    if request.method == 'POST':
        # Get shipping information
        shipping_address = request.POST.get('shipping_address', '').strip()
        shipping_city = request.POST.get('shipping_city', '').strip()
        shipping_state = request.POST.get('shipping_state', '').strip()
        shipping_phone = request.POST.get('shipping_phone', '').strip()
        
        # Validate shipping information
        if not all([shipping_address, shipping_city, shipping_state, shipping_phone]):
            messages.error(request, "Please fill in all shipping information")
            return render(request, 'main/checkout.html', {
                'cart_items': cart_data['items'],
                'cart_total': cart_data['total'],
                'cart_count': cart_data['count']
            })
        
        # Format full shipping address
        full_shipping_address = f"{shipping_address}, {shipping_city}, {shipping_state}. Phone: {shipping_phone}"
        
        try:
            with transaction.atomic():
                # Group items by seller
                items_by_seller = {}
                for item in cart_data['items']:
                    # Get seller from product or default to request.user (for marketplace)
                    seller = getattr(item['product'], 'seller', request.user)
                    
                    if seller not in items_by_seller:
                        items_by_seller[seller] = []
                    
                    items_by_seller[seller].append(item)
                
                # Create separate order for each seller
                created_orders = []
                
                for seller, items in items_by_seller.items():
                    # Calculate total for this seller's items
                    order_total = sum(item['subtotal'] for item in items)
                    
                    # Create order
                    order = Order.objects.create(
                        buyer=request.user,
                        seller=seller,
                        total_amount=order_total,
                        shipping_address=full_shipping_address,
                        status='pending',
                        payment_status='pending'
                    )
                    
                    # Create order items and reduce stock
                    for item in items:
                        OrderItem.objects.create(
                            order=order,
                            product=item['product'],
                            quantity=item['quantity'],
                            price=item['product'].price
                        )
                        
                        # Reduce product stock
                        product = item['product']
                        product.stock -= item['quantity']
                        product.save()
                    
                    created_orders.append(order)
                
                # Clear cart
                request.session['cart'] = {}
                request.session.modified = True
                
                # If only one order, redirect to payment
                if len(created_orders) == 1:
                    messages.success(request, "Order placed successfully! Please complete payment.")
                    return redirect('order_detail', order_id=created_orders[0].id)
                else:
                    # Multiple orders - redirect to orders page
                    messages.success(request, f"{len(created_orders)} orders placed successfully! Please complete payments.")
                    return redirect('my_orders')
        
        except Exception as e:
            messages.error(request, f"Error creating order: {str(e)}")
            return redirect('cart')
    
    # GET request - show checkout page
    context = {
        'cart_items': cart_data['items'],
        'cart_total': cart_data['total'],
        'cart_count': cart_data['count']
    }
    return render(request, 'main/checkout.html', context)


@login_required
def my_orders(request):
    """View all user's orders"""
    orders = Order.objects.filter(
        buyer=request.user
    ).prefetch_related(
        'items__product'
    ).order_by('-created_at')
    
    context = {
        'orders': orders
    }
    return render(request, 'main/my_orders.html', context)




def ajax_add_to_cart(request, product_id):
    """Add to cart via AJAX (doesn't require login for flexibility)"""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        
        if product.stock <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Product out of stock'
            })
        
        cart = get_cart(request)
        product_id_str = str(product_id)
        quantity = int(request.POST.get('quantity', 1))
        
        current_quantity = cart.get(product_id_str, 0)
        new_quantity = current_quantity + quantity
        
        if new_quantity > product.stock:
            return JsonResponse({
                'success': False,
                'message': f'Only {product.stock} units available'
            })
        
        cart[product_id_str] = new_quantity
        save_cart(request, cart)
        
        cart_data = get_cart_items(request)
        
        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart',
            'cart_count': cart_data['count'],
            'cart_total': str(cart_data['total'])
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def get_cart_count(request):
    """Get cart count via AJAX"""
    cart_data = get_cart_items(request)
    return JsonResponse({
        'count': cart_data['count'],
        'total': str(cart_data['total'])
    })


@require_POST
def set_currency(request):
    """
    Set user's preferred currency via AJAX POST.
    Expects 'currency' in POST data.
    """
    currency = request.POST.get('currency', '').upper()

    if currency in SUPPORTED_CURRENCIES:
        set_user_currency(request, currency)
        request.session.modified = True
        response = JsonResponse({'success': True})
        # Also set a cookie for convenience (expires in 30 days)
        response.set_cookie('currency', currency, max_age=30*24*60*60)
        return response

    return JsonResponse({'success': False, 'error': 'Invalid currency'}, status=400)


def get_currency_rates(request):
    """
    Return JSON of currency exchange rates relative to a base currency.
    GET params:
      - base: base currency code (default: 'NGN')
      - refresh: if '1' forces fetching updated rates
    """
    base = request.GET.get('base', 'NGN').upper()
    if base not in SUPPORTED_CURRENCIES:
        return JsonResponse({'success': False, 'error': 'Invalid base currency'}, status=400)

    # Optionally refresh rates (will call external API once)
    if request.GET.get('refresh') == '1':
        try:
            batch_update_rates(base_currency=base)
        except Exception:
            pass

    rates = {}
    for code in SUPPORTED_CURRENCIES.keys():
        if code == base:
            rates[code] = 1.0
        else:
            rate = get_exchange_rate(base, code)
            try:
                rates[code] = float(rate)
            except Exception:
                rates[code] = None

    return JsonResponse({'success': True, 'base': base, 'rates': rates})


@login_required
def order_detail(request, order_id):
    """View order details with payment options"""
    order = get_object_or_404(Order, id=order_id)
    
    # Check permissions
    if request.user not in [order.buyer, order.seller] and not request.user.is_staff:
        messages.error(request, "You don't have permission to view this order")
        return redirect('home')
    
    # Calculate escrow fee (2%)
    escrow_fee = order.total_amount * Decimal('0.02')
    escrow_total = order.total_amount + escrow_fee
    
    context = {
        'order': order,
        'escrow_fee': escrow_fee,
        'escrow_total': escrow_total,
    }
    return render(request, 'main/order_detail.html', context)


# ========================================
# NORMAL PAYMENT VIEWS
# ========================================

@login_required
def initiate_normal_payment(request, order_id):
    """Initiate normal payment (non-escrow) for an order"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    
    # Check if order is already paid
    if order.payment_status == 'paid':
        messages.warning(request, "This order has already been paid for")
        return redirect('order_detail', order_id=order.id)
    
    # Redirect to payment page
    return redirect('process_normal_payment', order_id=order.id)


@login_required
def process_normal_payment(request, order_id):
    """Process normal payment (non-escrow) using Flutterwave"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    
    if order.payment_status == 'paid':
        messages.success(request, "This order has already been paid for")
        return redirect('order_detail', order_id=order.id)
    
    # Initialize Flutterwave payment
    payment_data = initialize_normal_flutterwave_payment(order)
    
    if not payment_data.get('success'):
        messages.error(request, f"Payment initialization failed: {payment_data.get('message')}")
        return redirect('order_detail', order_id=order.id)
    
    context = {
        'order': order,
        'flutterwave_public_key': settings.FLUTTERWAVE_PUBLIC_KEY,
        'payment_link': payment_data.get('link'),
        'tx_ref': payment_data.get('tx_ref')
    }
    return render(request, 'main/payments/normal_payment.html', context)


@login_required
def normal_payment_callback(request):
    """Handle normal payment callback from Flutterwave"""
    transaction_id = request.GET.get('transaction_id')
    tx_ref = request.GET.get('tx_ref')
    status = request.GET.get('status')
    
    if status == 'successful' and transaction_id:
        try:
            # Extract order ID from tx_ref (format: ORDER-order_id-timestamp)
            order_id = tx_ref.split('-')[1]
            order = get_object_or_404(Order, id=order_id, buyer=request.user)
            
            # Verify the payment
            verification_result = verify_flutterwave_payment(transaction_id)
            
            if verification_result['success']:
                amount_paid = verification_result.get('amount', 0)
                expected_amount = float(order.total_amount)
                
                # Allow for small rounding differences
                if abs(amount_paid - expected_amount) < 0.01:
                    with transaction.atomic():
                        # Update order payment status
                        order.payment_status = 'paid'
                        order.payment_method = 'flutterwave'
                        order.payment_reference = transaction_id
                        order.paid_at = timezone.now()
                        order.status = 'processing'
                        order.save()
                        
                        # Credit seller's wallet
                        transfer_result = transfer_to_seller(order.seller, order.total_amount)
                        
                        # Create payment record
                        Payment.objects.create(
                            order=order,
                            user=request.user,
                            amount=amount_paid,
                            currency=verification_result.get('currency', 'NGN'),
                            payment_method='flutterwave',
                            reference=transaction_id,
                            status='successful',
                            completed_at=timezone.now(),
                            metadata={
                                'transfer_method': transfer_result.get('method'),
                                'transfer_message': transfer_result.get('message')
                            }
                        )
                    
                    messages.success(request, "Payment successful! Your order is being processed.")
                    return redirect('order_detail', order_id=order.id)
                else:
                    messages.error(request, f"Amount mismatch. Expected ₦{expected_amount:,.2f}, received ₦{amount_paid:,.2f}")
                    return redirect('process_normal_payment', order_id=order.id)
            else:
                messages.error(request, f"Payment verification failed: {verification_result.get('message')}")
                return redirect('process_normal_payment', order_id=order.id)
        except IndexError:
            messages.error(request, "Invalid payment reference format")
            return redirect('home')
        except Exception as e:
            messages.error(request, f"Error processing payment: {str(e)}")
            return redirect('home')
    
    elif status == 'cancelled':
        messages.warning(request, "Payment was cancelled.")
        try:
            order_id = tx_ref.split('-')[1]
            return redirect('order_detail', order_id=order_id)
        except:
            return redirect('home')
    else:
        messages.error(request, "Payment failed. Please try again.")
        return redirect('home')


@login_required
def payment_history(request):
    """View payment history for the logged-in user"""
    payments = Payment.objects.filter(user=request.user).select_related('order').order_by('-created_at')
    
    # Filter options
    status_filter = request.GET.get('status')
    if status_filter:
        payments = payments.filter(status=status_filter)
    
    context = {
        'payments': payments,
        'status_filter': status_filter
    }
    return render(request, 'main/payments/payment_history.html', context)


@login_required
def payment_detail(request, payment_id):
    """View details of a specific payment"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    context = {
        'payment': payment
    }
    return render(request, 'main/payments/payment_detail.html', context)


@csrf_exempt
def verify_payment_webhook(request):
    """
    Handle Flutterwave webhook notifications for payment events
    This is called by Flutterwave, not by users directly
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    # Verify webhook signature
    signature = request.headers.get('verif-hash')
    
    if hasattr(settings, 'FLUTTERWAVE_WEBHOOK_SECRET'):
        if signature != settings.FLUTTERWAVE_WEBHOOK_SECRET:
            return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=400)
    
    try:
        data = json.loads(request.body)
        event = data.get('event')
        
        if event == 'charge.completed':
            transaction_data = data.get('data', {})
            tx_ref = transaction_data.get('tx_ref')
            status = transaction_data.get('status')
            
            if status == 'successful':
                # Check transaction type
                if 'ESC-' in tx_ref:
                    # Escrow payment - import here to avoid circular imports
                    from escrow.models import EscrowTransaction
                    
                    try:
                        escrow_id = tx_ref.split('-')[-1]
                        escrow = EscrowTransaction.objects.get(id=escrow_id)
                        
                        if escrow.status == 'pending_payment':
                            with transaction.atomic():
                                escrow.status = 'in_escrow'
                                escrow.payment_received_at = timezone.now()
                                escrow.payment_reference = transaction_data.get('id')
                                escrow.save()
                        
                        # TODO: Send notifications
                        # send_notification(escrow.buyer, 'payment_confirmed', escrow)
                        # send_notification(escrow.seller, 'payment_received', escrow)
                    except EscrowTransaction.DoesNotExist:
                        pass
                
                elif 'ORDER-' in tx_ref:
                    # Normal payment
                    try:
                        order_id = tx_ref.split('-')[1]
                        order = Order.objects.get(id=order_id)
                        
                        if order.payment_status != 'paid':
                            with transaction.atomic():
                                order.payment_status = 'paid'
                                order.payment_reference = transaction_data.get('id')
                                order.paid_at = timezone.now()
                                order.status = 'processing'
                                order.save()
                                
                                # Credit seller
                                transfer_to_seller(order.seller, order.total_amount)
                        
                        # TODO: Send notifications
                        # send_notification(order.buyer, 'payment_confirmed', order)
                        # send_notification(order.seller, 'new_order', order)
                    except Order.DoesNotExist:
                        pass
        
        return JsonResponse({'status': 'success'}, status=200)
    
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)




def initialize_normal_flutterwave_payment(order):
    """Initialize normal (non-escrow) payment with Flutterwave"""
    url = "https://api.flutterwave.com/v3/payments"
    
    # Generate unique transaction reference
    tx_ref = f"ORDER-{order.id}-{int(timezone.now().timestamp())}"
    
    headers = {
        'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "tx_ref": tx_ref,
        "amount": str(order.total_amount),
        "currency": "NGN",  # Change based on your currency or user preference
        "redirect_url": f"{settings.SITE_URL}/payment/callback/",
        "payment_options": "card,banktransfer,ussd,mobilemoney,account",
        "customer": {
            "email": order.buyer.email,
            "phonenumber": getattr(order.buyer, 'phone', ''),
            "name": order.buyer.get_full_name()
        },
        "customizations": {
            "title": "Order Payment",
            "description": f"Payment for Order #{order.id}",
            "logo": f"{settings.SITE_URL}/static/img/logo.png"
        },
        "meta": {
            "order_id": order.id,
            "buyer_id": order.buyer.id,
            "payment_type": "normal"
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'success':
            return {
                'success': True,
                'link': data['data']['link'],
                'tx_ref': tx_ref
            }
        else:
            return {
                'success': False,
                'message': data.get('message', 'Payment initialization failed')
            }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'message': f'Network error: {str(e)}'
        }

def dashboard(request):
    """User dashboard view"""
    pass

def verify_flutterwave_payment(transaction_id):
    """Verify payment with Flutterwave"""
    url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
    
    headers = {
        'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'success':
            transaction_data = data.get('data', {})
            
            # Check if payment was successful
            if transaction_data.get('status') == 'successful':
                return {
                    'success': True,
                    'amount': float(transaction_data.get('amount', 0)),
                    'currency': transaction_data.get('currency'),
                    'transaction_id': transaction_id,
                    'reference': transaction_data.get('tx_ref')
                }
            else:
                return {
                    'success': False,
                    'message': f"Payment status: {transaction_data.get('status')}"
                }
        else:
            return {
                'success': False,
                'message': data.get('message', 'Verification failed')
            }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'message': f'Network error: {str(e)}'
        }


def transfer_to_seller(seller, amount):
    """
    Transfer funds to seller's account/wallet
    
    First tries to transfer to bank account via Flutterwave,
    falls back to crediting wallet if that fails
    """
    
    # Check if seller has bank account details
    if not hasattr(seller, 'bank_account'):
        # No bank account model - credit wallet directly
        wallet, created = Wallet.objects.get_or_create(user=seller)
        wallet.credit(amount)
        return {
            'success': True,
            'method': 'wallet',
            'message': 'Credited to wallet (no bank account linked)'
        }
    
    # Try bank transfer via Flutterwave
    url = "https://api.flutterwave.com/v3/transfers"
    
    headers = {
        'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "account_bank": seller.bank_account.bank_code,
        "account_number": seller.bank_account.account_number,
        "amount": float(amount),
        "currency": "NGN",
        "narration": "Payment for order",
        "reference": f"TRANSFER-{uuid.uuid4().hex[:12].upper()}",
        "callback_url": f"{settings.SITE_URL}/payment/transfer-callback/",
        "debit_currency": "NGN"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'success':
            return {
                'success': True,
                'method': 'bank_transfer',
                'reference': data['data'].get('reference'),
                'message': 'Bank transfer initiated'
            }
        else:
            # Fallback to wallet
            wallet, created = Wallet.objects.get_or_create(user=seller)
            wallet.credit(amount)
            return {
                'success': True,
                'method': 'wallet',
                'message': f"Bank transfer failed, credited to wallet: {data.get('message')}"
            }
    except Exception as e:
        # Fallback to wallet on any error
        wallet, created = Wallet.objects.get_or_create(user=seller)
        wallet.credit(amount)
        return {
            'success': True,
            'method': 'wallet',
            'message': f'Transfer error, credited to wallet: {str(e)}'
        }


# ========================================
# ESCROW HELPER FUNCTION
# (Used by escrow app)
# ========================================

def initialize_flutterwave_payment(escrow):
    """
    Initialize escrow payment with Flutterwave
    This function is called from escrow app
    """
    url = "https://api.flutterwave.com/v3/payments"
    
    # Generate unique transaction reference
    tx_ref = f"{escrow.transaction_id}-{escrow.id}"
    
    headers = {
        'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "tx_ref": tx_ref,
        "amount": str(escrow.total_amount),
        "currency": "NGN",
        "redirect_url": f"{settings.SITE_URL}/escrow/callback/",
        "payment_options": "card,banktransfer,ussd,mobilemoney",
        "customer": {
            "email": escrow.buyer.email,
            "phonenumber": getattr(escrow.buyer, 'phone', ''),
            "name": escrow.buyer.get_full_name()
        },
        "customizations": {
            "title": "Escrow Payment",
            "description": f"Payment for Order #{escrow.order.id}",
            "logo": f"{settings.SITE_URL}/static/img/logo.png"
        },
        "meta": {
            "escrow_id": escrow.id,
            "order_id": escrow.order.id
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'success':
            return {
                'success': True,
                'link': data['data']['link'],
                'tx_ref': tx_ref
            }
        else:
            return {
                'success': False,
                'message': data.get('message', 'Payment initialization failed')
            }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'message': f'Network error: {str(e)}'
        }