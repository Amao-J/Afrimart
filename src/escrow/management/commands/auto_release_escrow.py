
# Or set up as cron job to run hourly/daily

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from escrow.models import EscrowTransaction, EscrowStatusHistory
from main.views import transfer_to_seller


class Command(BaseCommand):
    help = 'Automatically release escrow funds after the auto-release period'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be released without actually releasing funds',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run = options['dry_run']
        
        # Find escrows ready for auto-release
        escrows_to_release = EscrowTransaction.objects.filter(
            status='delivered',
            auto_release_at__lte=now
        ).select_related('buyer', 'seller', 'order')
        
        total_count = escrows_to_release.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ No escrow funds ready for auto-release')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(f'\nFound {total_count} escrow(s) ready for auto-release')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n--- DRY RUN MODE (No changes will be made) ---\n')
            )
        
        released_count = 0
        failed_count = 0
        
        for escrow in escrows_to_release:
            days_since_delivery = (now - escrow.delivered_at).days if escrow.delivered_at else 0
            
            self.stdout.write(
                f'\n{"[DRY RUN] " if dry_run else ""}Processing Escrow {escrow.transaction_id}:'
            )
            self.stdout.write(f'  • Order: #{escrow.order.id}')
            self.stdout.write(f'  • Buyer: {escrow.buyer.username}')
            self.stdout.write(f'  • Seller: {escrow.seller.username}')
            self.stdout.write(f'  • Amount: ₦{escrow.amount:,.2f}')
            self.stdout.write(f'  • Delivered: {escrow.delivered_at.strftime("%Y-%m-%d %H:%M")}')
            self.stdout.write(f'  • Days since delivery: {days_since_delivery}')
            self.stdout.write(f'  • Auto-release date: {escrow.auto_release_at.strftime("%Y-%m-%d %H:%M")}')
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS('  ✓ Would release funds to seller')
                )
                released_count += 1
                continue
            
            try:
                with transaction.atomic():
                    # Transfer funds to seller
                    transfer_result = transfer_to_seller(escrow.seller, escrow.amount)
                    
                    if transfer_result.get('success'):
                        # Update escrow status
                        escrow.status = 'completed'
                        escrow.completed_at = now
                        escrow.save()
                        
                        # Log status change
                        EscrowStatusHistory.objects.create(
                            escrow=escrow,
                            old_status='delivered',
                            new_status='completed',
                            changed_by=None,  # System action
                            reason=f'Automatic release after {escrow.auto_release_days} days'
                        )
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Successfully released ₦{escrow.amount:,.2f} to {escrow.seller.username}'
                            )
                        )
                        self.stdout.write(f'  • Method: {transfer_result.get("method")}')
                        
                        released_count += 1
                        
                        # TODO: Send email notifications
                        # send_mail(
                        #     'Escrow Funds Released',
                        #     f'Your escrow funds of ₦{escrow.amount:,.2f} have been released.',
                        #     'noreply@techfy.ng',
                        #     [escrow.seller.email],
                        # )
                        
                    else:
                        raise Exception(transfer_result.get('message', 'Transfer failed'))
                
            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Failed to release funds: {str(e)}')
                )
                
                # Log the error (you might want to send admin notification)
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f'Auto-release failed for escrow {escrow.transaction_id}: {str(e)}'
                )
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'\nAuto-Release Summary:'))
        self.stdout.write(f'  Total found: {total_count}')
        self.stdout.write(
            self.style.SUCCESS(f'  Successfully released: {released_count}')
        )
        
        if failed_count > 0:
            self.stdout.write(
                self.style.ERROR(f'  Failed: {failed_count}')
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\n  Note: This was a dry run. No actual changes were made.')
            )
            self.stdout.write(
                self.style.WARNING(f'  Run without --dry-run to actually release funds.')
            )
        
        self.stdout.write('='*60 + '\n')