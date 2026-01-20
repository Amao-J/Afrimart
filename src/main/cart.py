from django.shortcuts import render, redirect, get_object_or_404
from decimal import Decimal
from .models import Product
from django.contrib import messages

def get_cart(request):
    """Get cart from session"""
    cart = request.session.get('cart', {})
    return cart


def save_cart(request, cart):
    """Save cart to session"""
    request.session['cart'] = cart
    request.session.modified = True


def get_cart_items(request):
    """Get cart items with product details and calculate totals"""
    cart = get_cart(request)
    cart_items = []
    total = Decimal('0.00')
    
    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=product_id)
            subtotal = product.price * quantity
            total += subtotal
            
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
        except Product.DoesNotExist:
            # Remove invalid product from cart
            del cart[product_id]
            save_cart(request, cart)
    
    return {
        'items': cart_items,
        'total': total,
        'count': sum(cart.values())
    }


# ========================================
# SHOPPING CART VIEWS
# ========================================

def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(Product, id=product_id)
    
    # Check stock
    if product.stock <= 0:
        messages.error(request, f"{product.name} is out of stock")
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    
    cart = get_cart(request)
    product_id_str = str(product_id)
    
    # Get quantity from POST or default to 1
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
    else:
        quantity = 1
    
    # Check if adding this quantity would exceed stock
    current_quantity = cart.get(product_id_str, 0)
    new_quantity = current_quantity + quantity
    
    if new_quantity > product.stock:
        messages.error(request, f"Only {product.stock} units available in stock")
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    
    # Add to cart
    cart[product_id_str] = new_quantity
    save_cart(request, cart)
    
    messages.success(request, f"{product.name} added to cart")
    return redirect('cart')


def update_cart(request, product_id):
    """Update product quantity in cart"""
    if request.method == 'POST':
        cart = get_cart(request)
        product_id_str = str(product_id)
        quantity = int(request.POST.get('quantity', 0))
        
        if quantity <= 0:
            # Remove from cart
            if product_id_str in cart:
                del cart[product_id_str]
                messages.success(request, "Item removed from cart")
        else:
            # Check stock
            product = get_object_or_404(Product, id=product_id)
            if quantity > product.stock:
                messages.error(request, f"Only {product.stock} units available")
                return redirect('cart')
            
            cart[product_id_str] = quantity
            messages.success(request, "Cart updated")
        
        save_cart(request, cart)
    
    return redirect('cart')


def remove_from_cart(request, product_id):
    """Remove product from cart"""
    cart = get_cart(request)
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        product = get_object_or_404(Product, id=product_id)
        del cart[product_id_str]
        save_cart(request, cart)
        messages.success(request, f"{product.name} removed from cart")
    
    return redirect('cart')


def clear_cart(request):
    """Clear entire cart"""
    request.session['cart'] = {}
    request.session.modified = True
    messages.success(request, "Cart cleared")
    return redirect('cart')


def cart_view(request):
    """Display shopping cart"""
    cart_data = get_cart_items(request)
    
    context = {
        'cart_items': cart_data['items'],
        'cart_total': cart_data['total'],
        'cart_count': cart_data['count']
    }
    return render(request, 'main/cart.html', context)

