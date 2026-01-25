from .utils.currency import get_user_currency, SUPPORTED_CURRENCIES


def cart_processor(request):
    """Add cart count to all templates"""
    cart = request.session.get('cart', {})
    cart_count = sum(cart.values())
    
    return {
        'cart_count': cart_count
    }


def currency_processor(request):
    """Add currency information to all templates"""
    currency = get_user_currency(request)

    return {
        'currency': currency,
        'user_currency': currency,  # alias used in templates
        'supported_currencies': SUPPORTED_CURRENCIES
    }