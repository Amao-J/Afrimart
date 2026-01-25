# main/utils/currency.py
"""
Currency conversion utilities for Techfy Africa
Supports multiple African currencies with real-time exchange rates
"""

import requests
from decimal import Decimal
from django.core.cache import cache
from django.conf import settings
try:
    from ..models import CurrencyRate
except ImportError:
    # Fallback if relative import fails
    try:
        from main.models import CurrencyRate
    except ImportError:
        CurrencyRate = None
import logging

logger = logging.getLogger(__name__)


# Supported currencies
SUPPORTED_CURRENCIES = {
    'NGN': {'name': 'Nigerian Naira', 'symbol': '₦', 'flag': '🇳🇬'},
    'USD': {'name': 'US Dollar', 'symbol': '$', 'flag': '🇺🇸'},
    'GHS': {'name': 'Ghana Cedi', 'symbol': '₵', 'flag': '🇬🇭'},
    'KES': {'name': 'Kenyan Shilling', 'symbol': 'KSh', 'flag': '🇰🇪'},
    'ZAR': {'name': 'South African Rand', 'symbol': 'R', 'flag': '🇿🇦'},
    'EUR': {'name': 'Euro', 'symbol': '€', 'flag': '🇪🇺'},
    'GBP': {'name': 'British Pound', 'symbol': '£', 'flag': '🇬🇧'},
}


def get_exchange_rate(from_currency='USD', to_currency='NGN', use_cache=True):
    """
    Get exchange rate from one currency to another
    Uses cache for 1 hour to reduce API calls
    
    Args:
        from_currency: Source currency code (default: USD)
        to_currency: Target currency code (default: NGN)
        use_cache: Whether to use cached rates (default: True)
    
    Returns:
        Decimal: Exchange rate
    """
    # If same currency, return 1
    if from_currency == to_currency:
        return Decimal('1.0')
    
    cache_key = f'exchange_rate_{from_currency}_{to_currency}'
    
    # Try cache first
    if use_cache:
        cached_rate = cache.get(cache_key)
        if cached_rate:
            logger.info(f"Using cached rate: 1 {from_currency} = {cached_rate} {to_currency}")
            return Decimal(str(cached_rate))
    
    # Try database
    try:
        rate_obj = CurrencyRate.objects.get(base=from_currency, quote=to_currency)
        cache.set(cache_key, float(rate_obj.rate), 3600)  # Cache for 1 hour
        logger.info(f"Using DB rate: 1 {from_currency} = {rate_obj.rate} {to_currency}")
        return rate_obj.rate
    except CurrencyRate.DoesNotExist:
        pass
    
    # Fetch from API
    rate = fetch_exchange_rate_from_api(from_currency, to_currency)
    
    if rate:
        # Save to database
        CurrencyRate.objects.update_or_create(
            base=from_currency,
            quote=to_currency,
            defaults={'rate': rate}
        )
        # Cache it
        cache.set(cache_key, float(rate), 3600)
        logger.info(f"Fetched new rate: 1 {from_currency} = {rate} {to_currency}")
        return rate
    
    # Fallback rates (if API fails)
    fallback_rates = get_fallback_rates()
    key = f"{from_currency}_{to_currency}"
    
    if key in fallback_rates:
        rate = Decimal(str(fallback_rates[key]))
        cache.set(cache_key, float(rate), 3600)
        logger.warning(f"Using fallback rate: 1 {from_currency} = {rate} {to_currency}")
        return rate
    
    logger.error(f"Could not get exchange rate for {from_currency} to {to_currency}")
    return Decimal('1.0')


def fetch_exchange_rate_from_api(from_currency='USD', to_currency='NGN'):
    """
    Fetch live exchange rate from ExchangeRate-API
    API returns rates with base currency
    Example: GET /v4/latest/NGN returns all rates from NGN
    """
    try:
        # Fetch rates with from_currency as base
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if the API returned rates
            if 'rates' in data and to_currency in data['rates']:
                rate = Decimal(str(data['rates'][to_currency]))
                logger.info(f"API Success: 1 {from_currency} = {rate} {to_currency}")
                return rate
            else:
                logger.warning(f"Currency {to_currency} not found in API response")
        else:
            logger.error(f"API returned status {response.status_code}")
        
    except requests.Timeout:
        logger.error("API request timed out")
    except requests.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching exchange rate: {str(e)}")
    
    return None


def get_fallback_rates():
    """
    Fallback exchange rates (updated: Jan 2025 based on actual API data)
    Used when API is unavailable
    """
    return {
        # From NGN (based on actual API response)
        'NGN_USD': 0.000702,
        'NGN_GHS': 0.00753,
        'NGN_KES': 0.0907,
        'NGN_ZAR': 0.0116,
        'NGN_EUR': 0.000606,
        'NGN_GBP': 0.000526,
        
        # From USD (calculated inverse)
        'USD_NGN': 1425.07,   # 1 / 0.000702
        'USD_GHS': 10.72,     # Approximate
        'USD_KES': 129.20,
        'USD_ZAR': 16.52,
        'USD_EUR': 0.86,
        'USD_GBP': 0.75,
        
        # From GHS
        'GHS_NGN': 132.80,
        'GHS_USD': 0.093,
        
        # From KES
        'KES_NGN': 11.03,
        'KES_USD': 0.0077,
        
        # From ZAR
        'ZAR_NGN': 86.21,
        'ZAR_USD': 0.061,
        
        # From EUR
        'EUR_NGN': 1650.17,
        'EUR_USD': 1.16,
        
        # From GBP
        'GBP_NGN': 1901.14,
        'GBP_USD': 1.33,
    }


def convert_currency(amount, from_currency='NGN', to_currency='USD'):
    """
    Convert amount from one currency to another
    
    Args:
        amount: Amount to convert (Decimal or float)
        from_currency: Source currency code
        to_currency: Target currency code
    
    Returns:
        Decimal: Converted amount
    """
    if from_currency == to_currency:
        return Decimal(str(amount))
    
    rate = get_exchange_rate(from_currency, to_currency)
    converted = Decimal(str(amount)) * rate
    
    return converted.quantize(Decimal('0.01'))


def format_currency(amount, currency='NGN'):
    """
    Format amount with currency symbol
    
    Args:
        amount: Amount to format (Decimal or float)
        currency: Currency code
    
    Returns:
        str: Formatted currency string
    """
    if currency not in SUPPORTED_CURRENCIES:
        currency = 'NGN'
    
    symbol = SUPPORTED_CURRENCIES[currency]['symbol']
    amount_decimal = Decimal(str(amount))
    
    # Format with thousand separators
    if amount_decimal >= 1000:
        formatted = f"{amount_decimal:,.2f}"
    else:
        formatted = f"{amount_decimal:.2f}"
    
    return f"{symbol}{formatted}"


def get_user_currency(request):
    """
    Get user's preferred currency from session or default
    
    Args:
        request: Django request object
    
    Returns:
        str: Currency code (e.g., 'NGN', 'USD')
    """
    # Check session
    currency = request.session.get('currency')
    
    if currency and currency in SUPPORTED_CURRENCIES:
        return currency
    
    # Default to NGN
    return 'NGN'


def set_user_currency(request, currency):
    """
    Set user's preferred currency in session
    
    Args:
        request: Django request object
        currency: Currency code to set
    """
    if currency in SUPPORTED_CURRENCIES:
        request.session['currency'] = currency
        logger.info(f"User currency set to {currency}")
        return True
    return False


def convert_price_to_user_currency(price, original_currency='NGN', request=None):
    """
    Convert price to user's preferred currency
    
    Args:
        price: Price in original currency
        original_currency: Original currency code
        request: Django request object (to get user's currency)
    
    Returns:
        dict: {'amount': Decimal, 'currency': str, 'formatted': str}
    """
    user_currency = get_user_currency(request) if request else 'NGN'
    
    if original_currency == user_currency:
        return {
            'amount': Decimal(str(price)),
            'currency': user_currency,
            'formatted': format_currency(price, user_currency)
        }
    
    converted_amount = convert_currency(price, original_currency, user_currency)
    
    return {
        'amount': converted_amount,
        'currency': user_currency,
        'formatted': format_currency(converted_amount, user_currency),
        'original_amount': Decimal(str(price)),
        'original_currency': original_currency,
        'rate': get_exchange_rate(original_currency, user_currency)
    }


def get_currency_info(currency_code):
    """
    Get currency information
    
    Args:
        currency_code: Currency code
    
    Returns:
        dict: Currency information
    """
    return SUPPORTED_CURRENCIES.get(currency_code, SUPPORTED_CURRENCIES['NGN'])


def batch_update_rates(base_currency='NGN'):
    """
    Update all currency rates at once
    More efficient than individual API calls
    
    Args:
        base_currency: Base currency to fetch rates for
    
    Returns:
        dict: Status of update
    """
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            rates_dict = data.get('rates', {})
            
            updated_count = 0
            for currency_code in SUPPORTED_CURRENCIES.keys():
                if currency_code != base_currency and currency_code in rates_dict:
                    rate = Decimal(str(rates_dict[currency_code]))
                    
                    # Save to database
                    CurrencyRate.objects.update_or_create(
                        base=base_currency,
                        quote=currency_code,
                        defaults={'rate': rate}
                    )
                    
                    # Cache it
                    cache_key = f'exchange_rate_{base_currency}_{currency_code}'
                    cache.set(cache_key, float(rate), 3600)
                    
                    updated_count += 1
                    logger.info(f"Updated: 1 {base_currency} = {rate} {currency_code}")
            
            return {
                'success': True,
                'updated': updated_count,
                'base': base_currency
            }
        else:
            logger.error(f"Batch update failed: HTTP {response.status_code}")
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except Exception as e:
        logger.error(f"Batch update error: {str(e)}")
        return {'success': False, 'error': str(e)}


# Template filter helpers
def currency_convert(amount, to_currency, from_currency='NGN'):
    """Template filter for currency conversion"""
    return convert_currency(amount, from_currency, to_currency)


def currency_format(amount, currency='NGN'):
    """Template filter for currency formatting"""
    return format_currency(amount, currency)