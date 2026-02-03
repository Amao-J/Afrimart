from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from main.models import Wallet, WalletTransaction
from decimal import Decimal
import uuid

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed wallet balances for users. Usage: python manage.py seed_wallets --amount=10000 --usernames=user1,user2 OR --all'

    def add_arguments(self, parser):
        parser.add_argument('--amount', type=str, required=True, help='Amount in NGN to seed each wallet (e.g., 10000)')
        parser.add_argument('--usernames', type=str, help='Comma-separated usernames to seed')
        parser.add_argument('--all', action='store_true', help='Seed all users')

    def handle(self, *args, **options):
        amount_str = options.get('amount')
        usernames = options.get('usernames')
        seed_all = options.get('all')

        try:
            amount = Decimal(str(amount_str))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Invalid amount: {amount_str}'))
            return

        if amount <= 0:
            self.stderr.write(self.style.ERROR('Amount must be greater than 0'))
            return

        users = []
        if seed_all:
            users = list(User.objects.all())
        elif usernames:
            names = [u.strip() for u in usernames.split(',') if u.strip()]
            users = list(User.objects.filter(username__in=names))
        else:
            self.stderr.write(self.style.ERROR('No users specified. Use --usernames or --all'))
            return

        seeded = 0
        for user in users:
            wallet, _ = Wallet.objects.get_or_create(user=user)
            try:
                wallet.credit(amount)
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=amount,
                    transaction_type='seed',
                    description='Seeded via management command',
                    reference=f'SEED-{uuid.uuid4().hex[:10].upper()}'
                )
                self.stdout.write(self.style.SUCCESS(f'Seeded {user.username} with ₦{amount:,.2f}'))
                seeded += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Failed to seed {user.username}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'Done. Seeded {seeded} wallet(s)'))