# Automated Commands Setup Guide

## 📋 Commands Overview

You now have two powerful management commands to automate your e-commerce platform:

### 1. **Auto-Release Escrow Funds**
Automatically releases escrow funds to sellers after the delivery confirmation period.

### 2. **Unlock Stock from Unpaid Orders**
Returns stock to inventory from orders that haven't been paid within a specified timeframe.

---

## 🚀 Installation

### Step 1: Create Directory Structure

For **Escrow Command**:
```bash
mkdir -p escrow/management/commands
touch escrow/management/__init__.py
touch escrow/management/commands/__init__.py
```

For **Stock Unlock Command**:
```bash
mkdir -p main/management/commands
touch main/management/__init__.py
touch main/management/commands/__init__.py
```

### Step 2: Copy Command Files

- Copy `auto_release_escrow.py` to `escrow/management/commands/`
- Copy `unlock_unpaid_orders.py` to `main/management/commands/`

---

## 🎯 Usage

### Auto-Release Escrow Command

**Basic Usage:**
```bash
python manage.py auto_release_escrow
```

**Dry Run (Preview without changes):**
```bash
python manage.py auto_release_escrow --dry-run
```

**What it does:**
- ✅ Finds all escrow transactions with status "delivered"
- ✅ Checks if auto-release date has passed
- ✅ Transfers funds to seller's wallet/bank account
- ✅ Updates escrow status to "completed"
- ✅ Logs the action in status history
- ✅ Shows detailed summary of all actions

**Example Output:**
```
Found 3 escrow(s) ready for auto-release

Processing Escrow ESC-ABC123DEF456:
  • Order: #127
  • Buyer: john_doe
  • Seller: tech_shop
  • Amount: ₦850,000.00
  • Delivered: 2025-01-03 14:30
  • Days since delivery: 7
  • Auto-release date: 2025-01-10 14:30
  ✓ Successfully released ₦850,000.00 to tech_shop
  • Method: wallet

============================================================
Auto-Release Summary:
  Total found: 3
  Successfully released: 3
  Failed: 0
============================================================
```

---

### Unlock Stock Command

**Basic Usage (24 hours):**
```bash
python manage.py unlock_unpaid_orders
```

**Custom Time Period:**
```bash
# Unlock after 48 hours
python manage.py unlock_unpaid_orders --hours=48

# Unlock after 6 hours
python manage.py unlock_unpaid_orders --hours=6
```

**Dry Run (Preview):**
```bash
python manage.py unlock_unpaid_orders --dry-run
```

**Cancel Orders Too:**
```bash
python manage.py unlock_unpaid_orders --cancel-orders
```

**Combined Options:**
```bash
# Preview what would happen after 12 hours
python manage.py unlock_unpaid_orders --hours=12 --dry-run

# Actually unlock and cancel after 24 hours
python manage.py unlock_unpaid_orders --hours=24 --cancel-orders
```

**What it does:**
- ✅ Finds unpaid orders older than specified hours
- ✅ Returns stock to each product
- ✅ Optionally cancels the orders
- ✅ Shows detailed summary
- ✅ Prevents overselling

**Example Output:**
```
Found 5 unpaid order(s) older than 24 hours

Processing Order #123:
  • Buyer: jane_smith
  • Created: 2025-01-09 10:00
  • Hours old: 26.5
  • Total: ₦520,000.00
  • Items: 2
    ✓ Unlocked 1 × iPhone 14 Pro Max (Stock: 14 → 15)
    ✓ Unlocked 2 × AirPods Pro (Stock: 28 → 30)
    ✓ Order marked as cancelled

============================================================
Stock Unlock Summary:
  Orders processed: 5/5
  Items unlocked: 12
  Total stock returned: 18 units
  Orders cancelled: 5
============================================================
```

---

## ⏰ Automated Scheduling

### Option 1: Cron Jobs (Linux/Mac)

Edit crontab:
```bash
crontab -e
```

Add these lines:

```bash
# Auto-release escrow funds every hour
0 * * * * cd /path/to/project && /path/to/venv/bin/python manage.py auto_release_escrow >> /var/log/escrow_release.log 2>&1

# Unlock stock from unpaid orders every 6 hours
0 */6 * * * cd /path/to/project && /path/to/venv/bin/python manage.py unlock_unpaid_orders --cancel-orders >> /var/log/stock_unlock.log 2>&1

# Or run unlock daily at 2 AM
0 2 * * * cd /path/to/project && /path/to/venv/bin/python manage.py unlock_unpaid_orders --hours=24 --cancel-orders >> /var/log/stock_unlock.log 2>&1
```

**Cron Schedule Examples:**
```
*/30 * * * *     # Every 30 minutes
0 * * * *        # Every hour
0 */6 * * *      # Every 6 hours
0 0 * * *        # Daily at midnight
0 2 * * *        # Daily at 2 AM
0 0 * * 0        # Weekly on Sunday
```

### Option 2: Celery Beat (Recommended for Production)

**Install Celery:**
```bash
pip install celery redis
```

**Configure Celery (app/celery.py):**
```python
from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

app = Celery('techfy')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Schedule tasks
app.conf.beat_schedule = {
    'auto-release-escrow-hourly': {
        'task': 'escrow.tasks.auto_release_escrow_funds',
        'schedule': crontab(minute=0),  # Every hour
    },
    'unlock-unpaid-orders-daily': {
        'task': 'main.tasks.unlock_unpaid_stock',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
```

**Create Tasks (escrow/tasks.py):**
```python
from celery import shared_task
from django.core.management import call_command

@shared_task
def auto_release_escrow_funds():
    call_command('auto_release_escrow')

@shared_task
def unlock_unpaid_stock():
    call_command('unlock_unpaid_orders', hours=24, cancel_orders=True)
```

**Run Celery:**
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery Worker
celery -A app worker -l info

# Terminal 3: Start Celery Beat
celery -A app beat -l info
```

### Option 3: Django-Cron

**Install:**
```bash
pip install django-cron
```

**Add to settings.py:**
```python
INSTALLED_APPS = [
    # ...
    'django_cron',
]

CRON_CLASSES = [
    'escrow.cron.AutoReleaseEscrowCronJob',
    'main.cron.UnlockUnpaidOrdersCronJob',
]
```

**Create Cron Jobs (escrow/cron.py):**
```python
from django_cron import CronJobBase, Schedule
from django.core.management import call_command

class AutoReleaseEscrowCronJob(CronJobBase):
    RUN_EVERY_MINS = 60  # Every hour
    
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'escrow.auto_release_escrow'
    
    def do(self):
        call_command('auto_release_escrow')

class UnlockUnpaidOrdersCronJob(CronJobBase):
    RUN_AT_TIMES = ['02:00']  # Daily at 2 AM
    
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'main.unlock_unpaid_orders'
    
    def do(self):
        call_command('unlock_unpaid_orders', hours=24, cancel_orders=True)
```

**Run manually:**
```bash
python manage.py runcrons
```

---

## 🔔 Email Notifications (Optional)

Add email notifications to your commands:

**Update settings.py:**
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'Techfy-NG <noreply@techfy.ng>'
```

**In auto_release_escrow.py, uncomment:**
```python
from django.core.mail import send_mail

# After successful release:
send_mail(
    'Escrow Funds Released',
    f'Your escrow funds of ₦{escrow.amount:,.2f} have been released to your account.',
    'noreply@techfy.ng',
    [escrow.seller.email],
    fail_silently=True,
)
```

**In unlock_unpaid_orders.py, add:**
```python
from django.core.mail import send_mail

# After cancelling order:
if cancel_orders:
    send_mail(
        'Order Cancelled - Payment Not Received',
        f'Your order #{order.id} has been cancelled due to non-payment.',
        'noreply@techfy.ng',
        [order.buyer.email],
        fail_silently=True,
    )
```

---

## 📊 Monitoring & Logging

### Set up logging in settings.py:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'escrow_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/escrow_release.log',
            'formatter': 'verbose',
        },
        'stock_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/stock_unlock.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'escrow': {
            'handlers': ['escrow_file'],
            'level': 'INFO',
        },
        'main': {
            'handlers': ['stock_file'],
            'level': 'INFO',
        },
    },
}
```

Create logs directory:
```bash
mkdir logs
```

---

## ✅ Best Practices

### 1. Always Test First
```bash
# Run dry-run before actual execution
python manage.py auto_release_escrow --dry-run
python manage.py unlock_unpaid_orders --dry-run
```

### 2. Monitor Logs
```bash
# Watch escrow releases
tail -f /var/log/escrow_release.log

# Watch stock unlocks
tail -f /var/log/stock_unlock.log
```

### 3. Set Appropriate Timeframes
- **Escrow auto-release**: 7 days (default in model)
- **Stock unlock**: 24-48 hours (configurable)

### 4. Database Backups
Run commands during low-traffic periods and always have recent backups.

### 5. Alert on Failures
Set up email alerts for admin when commands fail:

```python
# In command, add:
if failed_count > 0:
    send_mail(
        'Command Failed',
        f'{failed_count} items failed to process',
        'noreply@techfy.ng',
        ['admin@techfy.ng'],
    )
```

---

## 🐛 Troubleshooting

### Commands not found?
```bash
# Make sure __init__.py files exist
touch main/management/__init__.py
touch main/management/commands/__init__.py
touch escrow/management/__init__.py
touch escrow/management/commands/__init__.py

# Restart Django
python manage.py runserver
```

### Cron not running?
```bash
# Check cron logs
sudo tail -f /var/log/syslog | grep CRON

# Test command manually
python manage.py auto_release_escrow
```

### Permission errors?
```bash
# Make sure scripts are executable
chmod +x manage.py

# Check file ownership
ls -la main/management/commands/
```

---

## 🎉 You're All Set!

Your e-commerce platform now has:
- ✅ Automatic escrow fund releases
- ✅ Automatic stock recovery from unpaid orders
- ✅ Dry-run mode for testing
- ✅ Detailed logging
- ✅ Flexible scheduling options

Run the commands manually or set them up to run automatically! 🚀
