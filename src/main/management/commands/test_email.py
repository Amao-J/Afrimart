# main/management/commands/test_all_emails.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings

class Command(BaseCommand):
    help = 'Test all email functionalities'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str)

    def handle(self, *args, **options):
        recipient = options['email']
        
        tests = [
            self.test_simple_email,
            self.test_html_email,
            self.test_email_with_attachment,
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                test(recipient)
                passed += 1
                self.stdout.write(self.style.SUCCESS(f'✓ {test.__name__} passed'))
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f'✗ {test.__name__} failed: {str(e)}'))
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Tests passed: {passed}/{len(tests)}')
        self.stdout.write(f'Tests failed: {failed}/{len(tests)}')

    def test_simple_email(self, recipient):
        """Test simple text email"""
        send_mail(
            'Simple Email Test',
            'This is a simple text email.',
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )

    def test_html_email(self, recipient):
        """Test HTML email"""
        msg = EmailMultiAlternatives(
            'HTML Email Test',
            'Plain text version',
            settings.DEFAULT_FROM_EMAIL,
            [recipient]
        )
        msg.attach_alternative('<h1>This is HTML!</h1>', "text/html")
        msg.send()

    def test_email_with_attachment(self, recipient):
        """Test email with attachment"""
        from django.core.mail import EmailMessage
        
        msg = EmailMessage(
            'Email with Attachment',
            'This email has an attachment.',
            settings.DEFAULT_FROM_EMAIL,
            [recipient]
        )
        
        # Create a simple text file attachment
        msg.attach('test.txt', 'This is a test attachment.', 'text/plain')
        msg.send()