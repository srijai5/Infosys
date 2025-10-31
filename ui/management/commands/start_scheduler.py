import os
import django
import time
from django.core.management.base import BaseCommand
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.mail import send_mail
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infosys.settings')
django.setup()

def send_reminder_email(time_of_day):
    """Send reminder email"""
    try:
        send_mail(
            subject=f'📚 {time_of_day.capitalize()} Reminder: Continue Your Courses',
            message=f'Hello! This is your {time_of_day} reminder to continue your courses on StudyTrack.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['nvasanthi2005@gmail.com'],
            fail_silently=False,
        )
        print(f"✅ {time_of_day.capitalize()} email sent to nvasanthi2005@gmail.com")
    except Exception as e:
        print(f"❌ Error sending {time_of_day} email: {str(e)}")

class Command(BaseCommand):
    help = 'Start the email scheduler'

    def handle(self, *args, **options):
        scheduler = BackgroundScheduler()
        
        # For testing: Run every 2 minutes
        # Remove this in production and use the cron schedules below
        scheduler.add_job(
            send_reminder_email,
            'interval',
            minutes=2,
            args=['test'],
            id='test_reminder'
        )
        
        # Schedule morning reminder (9 AM daily) - UNCOMMENT FOR PRODUCTION
        # scheduler.add_job(
        #     send_reminder_email,
        #     'cron',
        #     hour=9,
        #     minute=0,
        #     args=['morning'],
        #     id='morning_reminder'
        # )
        
        # Schedule afternoon reminder (2 PM daily) - UNCOMMENT FOR PRODUCTION
        # scheduler.add_job(
        #     send_reminder_email,
        #     'cron',
        #     hour=14,
        #     minute=0,
        #     args=['afternoon'],
        #     id='afternoon_reminder'
        # )
        
        # Schedule evening reminder (7 PM daily) - UNCOMMENT FOR PRODUCTION
        # scheduler.add_job(
        #     send_reminder_email,
        #     'cron',
        #     hour=19,
        #     minute=0,
        #     args=['evening'],
        #     id='evening_reminder'
        # )
        
        scheduler.start()
        print("✅ Email scheduler started!")
        print("📧 Test emails will send every 2 minutes")
        print("🛑 Press Ctrl+C to stop the scheduler")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("🛑 Stopping scheduler...")
            scheduler.shutdown()