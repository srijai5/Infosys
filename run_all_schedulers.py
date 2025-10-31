# combined_reminder_scheduler.py
import os
import django
import sys
import time
import threading
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infosys.settings')

try:
    django.setup()

    from django.core.management import call_command

    class CombinedReminderScheduler:
        def __init__(self):
            self.setup_logging()
            self.scheduler = BackgroundScheduler()
            
        def setup_logging(self):
            print('🎯 MILESTONE 4 - COMBINED REMINDER SYSTEM')
            print('=========================================')
            print('📅 COURSE REMINDERS:')
            print('   🕘 9:00 AM - Morning Course Reminders')
            print('   🕑 2:00 PM - Afternoon Course Reminders')
            print('   🕖 7:00 PM - Evening Course Reminders')
            print('')
            print('📅 QUIZ REMINDERS:')
            print('   🕘 9:00 AM - Daily Quiz Reminders')
            print('=========================================')
            print('🤖 Both systems running in single scheduler')
            print('🛑 Press Ctrl+C to stop\n')
        
        def send_course_reminders(self, time_of_day):
            """Send course reminders"""
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f'📚 [{current_time}] Sending {time_of_day.upper()} COURSE reminders...')
            try:
                # Import and call your course reminder function
                from ui.utils import send_course_reminder_email
                from ui.models import BaseUser, StudentCourse
                
                students = BaseUser.objects.filter(user_type='student')
                email_count = 0
                
                for student in students:
                    if student.email:
                        student_courses = StudentCourse.objects.filter(student=student)
                        for enrollment in student_courses:
                            progress = getattr(enrollment, 'course_progress', 0)
                            if progress < 100:  # Only incomplete courses
                                send_course_reminder_email(student, enrollment)
                                email_count += 1
                
                print(f'   ✅ {time_of_day.upper()} COURSES: {email_count} emails sent')
                
            except Exception as e:
                print(f'   ❌ Course reminder error: {e}')
        
        def send_quiz_reminders(self, time_of_day):
            """Send quiz reminders"""
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f'📝 [{current_time}] Sending {time_of_day.upper()} QUIZ reminders...')
            try:
                call_command('send_daily_quiz_reminders')
                print(f'   ✅ {time_of_day.upper()} QUIZZES: Reminders sent successfully')
            except Exception as e:
                print(f'   ❌ Quiz reminder error: {e}')

        def start_scheduler(self):
            # COURSE REMINDERS (3x daily)
            self.scheduler.add_job(
                lambda: self.send_course_reminders('morning'),
                CronTrigger(hour=9, minute=0),
                id='morning_courses'
            )
            self.scheduler.add_job(
                lambda: self.send_course_reminders('afternoon'),
                CronTrigger(hour=2, minute=0),
                id='afternoon_courses'
            )
            self.scheduler.add_job(
                lambda: self.send_course_reminders('evening'),
                CronTrigger(hour=17, minute=12s),
                id='evening_courses'
            )
            
            # QUIZ REMINDERS (1x daily)
            self.scheduler.add_job(
                lambda: self.send_quiz_reminders('daily'),
                CronTrigger(hour=17, minute=13),  # 5 minutes after course reminders
                id='daily_quizzes'
            )
            
            self.scheduler.start()
            print("✅ COMBINED SCHEDULER STARTED!")
            print("⏰ Next reminders at their scheduled times")

    # Start the combined scheduler
    scheduler = CombinedReminderScheduler()
    scheduler.start_scheduler()

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n🛑 Stopping combined scheduler...')
        scheduler.scheduler.shutdown()

except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()