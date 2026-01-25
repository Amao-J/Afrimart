# main/management/commands/update_currency_rates.py
"""
Management command to update currency exchange rates
Run with: python manage.py update_currency_rates
Or set up as cron job to run daily
"""

from django.core.management.base import BaseCommand
from main.utils.currency import batch_update_rates, SUPPORTED_CURRENCIES


class Command(BaseCommand):
    help = 'Update currency exchange rates from API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base',
            type=str,
            default='NGN',
            help='Base currency (default: NGN)',
        )

    def handle(self, *args, **options):
        base_currency = options['base']
        
        self.stdout.write(
            self.style.WARNING(f'\nUpdating exchange rates with base: {base_currency}')
        )
        self.stdout.write('='*60 + '\n')
        
        # Use batch update (single API call)
        result = batch_update_rates(base_currency)
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Successfully updated {result["updated"]} exchange rates')
            )
            
            # Show sample rates
            from main.models import CurrencyRate
            self.stdout.write('\nSample rates:')
            
            sample_currencies = ['USD', 'GHS', 'KES', 'ZAR', 'EUR', 'GBP']
            for currency in sample_currencies:
                if currency != base_currency:
                    try:
                        rate = CurrencyRate.objects.get(base=base_currency, quote=currency)
                        self.stdout.write(
                            f'  1 {base_currency} = {rate.rate} {currency}'
                        )
                    except CurrencyRate.DoesNotExist:
                        pass
        else:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Update failed: {result.get("error")}')
            )
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(
            self.style.SUCCESS('\nUpdate Summary:')
        )
        self.stdout.write(f'  Base currency: {base_currency}')
        self.stdout.write(f'  Supported currencies: {len(SUPPORTED_CURRENCIES)}')
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(f'  Successfully updated: {result["updated"]}')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'  Status: Failed')
            )
        
        self.stdout.write('='*60 + '\n')