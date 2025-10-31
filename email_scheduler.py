import os
import django
import sys
import time
from apscheduler.schedulers.background import BackgroundScheduler

sys.path.append('.')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infosys.settings')

try:
    django.setup()
    
    from django.core.mail import send_mail
    from django.conf import settings
    
    def send_reminder_email(time_of_day):
        try:
            send_mail(
                subject=f'{time_of_day.capitalize()} Reminder: Continue Your Courses',
                message=f'Hello! This is your {time_of_day} reminder to continue your courses on StudyTrack.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['nvasanthi2005@gmail.com'],
                fail_silently=False,
            )
            print(f'SUCCESS: {time_of_day.capitalize()} email sent to nvasanthi2005@gmail.com')
        except Exception as e:
            print(f'ERROR: {e}')

    scheduler = BackgroundScheduler()
    
    # TEST: Send every 2 minutes (for demonstration)
    scheduler.add_job(
        send_reminder_email,
        'interval',
        minutes=2,
        args=['test'],
        id='test_reminder'
    )
    
    scheduler.start()
    print('SUCCESS: Automated email scheduler started!')
    print('Test emails will send every 2 minutes')
    print('Press Ctrl+C to stop the scheduler')
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Stopping scheduler...')
        scheduler.shutdown()
        
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
