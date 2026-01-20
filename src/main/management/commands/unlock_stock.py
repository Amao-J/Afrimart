# main/management/commands/unlock_unpaid_orders.py
# Run with: python manage.py unlock_unpaid_orders
# Or set up as cron job to run daily

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from main.models import Order, OrderItem, Product


class Command(BaseCommand):
    help = 'Unlock stock from unpaid orders after a specified time period'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=4,
            help='Number of hours to wait before unlocking stock (default: 4)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be unlocked without actually unlocking stock',
        )
        parser.add_argument(
            '--cancel-orders',
            action='store_true',
            help='Also cancel the orders (mark as cancelled)',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        cancel_orders = options['cancel_orders']
        
        now = timezone.now()
        cutoff_time = now - timedelta(hours=hours)
        
        # Find unpaid orders older than cutoff time
        unpaid_orders = Order.objects.filter(
            payment_status='pending',
            created_at__lt=cutoff_time,
            status='pending'
        ).prefetch_related('items__product')
        
        total_count = unpaid_orders.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS(f'✓ No unpaid orders older than {hours} hours found')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(f'\nFound {total_count} unpaid order(s) older than {hours} hours')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n--- DRY RUN MODE (No changes will be made) ---\n')
            )
        
        total_items_unlocked = 0
        total_stock_unlocked = 0
        orders_processed = 0
        errors = 0
        
        for order in unpaid_orders:
            hours_old = (now - order.created_at).total_seconds() / 3600
            
            self.stdout.write(f'\n{"[DRY RUN] " if dry_run else ""}Processing Order #{order.id}:')
            self.stdout.write(f'  • Buyer: {order.buyer.username}')
            self.stdout.write(f'  • Created: {order.created_at.strftime("%Y-%m-%d %H:%M")}')
            self.stdout.write(f'  • Hours old: {hours_old:.1f}')
            self.stdout.write(f'  • Total: ₦{order.total_amount:,.2f}')
            self.stdout.write(f'  • Items: {order.items.count()}')
            
            if dry_run:
                # Just show what would be done
                for item in order.items.all():
                    self.stdout.write(
                        f'    - Would unlock {item.quantity} × {item.product.name} '
                        f'(Current stock: {item.product.stock})'
                    )
                    total_items_unlocked += 1
                    total_stock_unlocked += item.quantity
                
                if cancel_orders:
                    self.stdout.write(
                        self.style.WARNING('    - Would cancel order')
                    )
                
                orders_processed += 1
                continue
            
            # Actually process the order
            try:
                with transaction.atomic():
                    # Unlock stock for each item
                    for item in order.items.all():
                        product = item.product
                        old_stock = product.stock
                        product.stock += item.quantity
                        product.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'    ✓ Unlocked {item.quantity} × {product.name} '
                                f'(Stock: {old_stock} → {product.stock})'
                            )
                        )
                        
                        total_items_unlocked += 1
                        total_stock_unlocked += item.quantity
                    
                    # Optionally cancel the order
                    if cancel_orders:
                        order.status = 'cancelled'
                        order.payment_status = 'failed'
                        order.save()
                        self.stdout.write(
                            self.style.WARNING('    ✓ Order marked as cancelled')
                        )
                    
                    orders_processed += 1
                    
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'    ✗ Error processing order: {str(e)}')
                )
                
                # Log the error
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Failed to unlock stock for order {order.id}: {str(e)}')
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'\nStock Unlock Summary:'))
        self.stdout.write(f'  Orders processed: {orders_processed}/{total_count}')
        self.stdout.write(f'  Items unlocked: {total_items_unlocked}')
        self.stdout.write(f'  Total stock returned: {total_stock_unlocked} units')
        
        if cancel_orders and not dry_run:
            self.stdout.write(f'  Orders cancelled: {orders_processed}')
        
        if errors > 0:
            self.stdout.write(
                self.style.ERROR(f'  Errors: {errors}')
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\n  Note: This was a dry run. No actual changes were made.')
            )
            self.stdout.write(
                self.style.WARNING(f'  Run without --dry-run to actually unlock stock.')
            )
        
        self.stdout.write('='*60 + '\n')


class Command_Alternative(BaseCommand):
    """
    Alternative version with more options
    This gives you flexibility to choose different strategies
    """
    help = 'Unlock stock from unpaid orders with advanced options'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=4,
            help='Hours to wait before unlocking (default: 4)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview without making changes',
        )
        parser.add_argument(
            '--status',
            choices=['pending', 'processing', 'all'],
            default='pending',
            help='Order status to process (default: pending)',
        )
        parser.add_argument(
            '--payment-status',
            choices=['pending', 'failed', 'all'],
            default='pending',
            help='Payment status to process (default: pending)',
        )
        parser.add_argument(
            '--action',
            choices=['unlock', 'cancel', 'both'],
            default='unlock',
            help='Action to take: unlock stock, cancel order, or both (default: unlock)',
        )
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Send email notification to buyers',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        action = options['action']
        send_email = options['send_email']
        
        # Build query based on options
        now = timezone.now()
        cutoff_time = now - timedelta(hours=hours)
        
        query = Order.objects.filter(created_at__lt=cutoff_time)
        
        if options['status'] != 'all':
            query = query.filter(status=options['status'])
        
        if options['payment_status'] != 'all':
            query = query.filter(payment_status=options['payment_status'])
        
        orders = query.prefetch_related('items__product')
        
        # Process orders...
        # (Similar to above but with more flexibility based on options)
        pass