# quiz_reminder_scheduler.py
import os
import django
import sys
import time
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

sys.path.append('.')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infosys.settings')

try:
    django.setup()

    from django.core.management import call_command
    from ui.models import Quiz, BaseUser, StudentCourse, QuizAttempt

    class QuizReminderScheduler:
        def __init__(self):
            self.setup_logging()
            
        def setup_logging(self):
            print('🎯 MILESTONE 4 - DAILY QUIZ REMINDER SCHEDULER ACTIVATED!')
            print('=========================================================')
            print('📅 DAILY QUIZ REMINDER SCHEDULE:')
            print('   🕘 9:00 AM - Daily Quiz Reminders (ONCE DAILY)')
            print('=========================================================')
            print('📧 Quiz reminders will send ONCE per day at 9:00 AM')
            print('🛑 Press Ctrl+C to stop the scheduler\n')
        
        def send_daily_quiz_reminders(self, time_of_day):
            """Send daily quiz reminders to all students with pending quizzes"""
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f'\n⏰ {current_time} - Sending {time_of_day.upper()} QUIZ reminders...')
            print('=' * 60)
            
            try:
                # Call the management command
                from django.core.management import call_command
                
                print(f'🚀 Running daily quiz reminder command...')
                
                # Call your management command
                call_command('send_daily_quiz_reminders')
                
                print(f'✅ {time_of_day.upper()} QUIZ REMINDERS COMPLETED!')
                print(f'⏰ Next reminder tomorrow at 9:00 AM')
                print('=' * 60)
                    
            except Exception as e:
                print(f'❌ ERROR in {time_of_day} quiz reminders: {e}')
                import traceback
                traceback.print_exc()

    # Initialize the scheduler
    scheduler = QuizReminderScheduler()

    # Create APScheduler instance
    aps_scheduler = BackgroundScheduler()

    # 🎯 DAILY SCHEDULE: Send quiz reminders ONCE per day at 9:00 AM
    aps_scheduler.add_job(
        lambda: scheduler.send_daily_quiz_reminders('daily'),
        CronTrigger(hour=9, minute=5),  # 9:00 AM DAILY
        id='daily_quiz_reminder'
    )

    # Start the scheduler
    aps_scheduler.start()

    print("\n⏰ DAILY QUIZ REMINDER SCHEDULER STARTED!")
    print("📧 Quiz reminders will send:")
    print("   🕘 ONCE DAILY at 9:00 AM")
    print("   📊 All pending quizzes")
    print("   👥 All enrolled students")
    print("   🎯 Automatic & No manual intervention")
    print("\n⏰ Next scheduled run:")
    print("   Tomorrow at 9:00 AM")
    print("🛑 Press Ctrl+C to stop the scheduler\n")

    # Optional: Send immediately for testing (comment out for production)
    # print("🚀 Sending initial test reminder...")
    # scheduler.send_daily_quiz_reminders('INITIAL TEST')
    # print("✅ Initial test completed. Waiting for scheduled runs...")

    # Keep the scheduler running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n🛑 Stopping daily quiz reminder scheduler...')
        aps_scheduler.shutdown()

except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()