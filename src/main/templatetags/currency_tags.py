from django import template
from decimal import Decimal

register = template.Library()

# Import helper functions from the utils module
from main.utils.currency import (
    currency_convert,
    currency_format,
    convert_price_to_user_currency,
    get_user_currency,
)


@register.filter(name='currency_format')
def currency_format_filter(amount, currency='NGN'):
    """Format an amount with the given currency symbol."""
    try:
        return currency_format(amount, currency)
    except Exception:
        return str(amount)


@register.filter(name='currency_convert')
def currency_convert_filter(amount, to_currency, from_currency='NGN'):
    """Convert amount from one currency to another and return Decimal."""
    try:
        return currency_convert(amount, to_currency, from_currency)
    except Exception:
        return Decimal('0.00')


@register.simple_tag(takes_context=True)
def format_price(context, price, original_currency='NGN'):
    """Return a formatted price string in the user's preferred currency."""
    request = context.get('request')
    try:
        conv = convert_price_to_user_currency(price, original_currency, request)
        return conv.get('formatted', str(price))
    except Exception:
        return str(price)


@register.simple_tag(takes_context=True)
def current_currency(context):
    """Return the current currency code for the request (e.g., NGN)."""
    request = context.get('request')
    try:
        return get_user_currency(request)
    except Exception:
        return 'NGN'