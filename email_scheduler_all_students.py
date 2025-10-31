import os
import django
import sys
import time
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

sys.path.append('.')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infosys.settings')

try:
    django.setup()

    # Import only what exists and works
    from ui.models import BaseUser, StudentCourse
    from ui.utils import send_course_reminder_email

    class EmailScheduler:
        def __init__(self):
            self.setup_logging()
            
        def setup_logging(self):
            print('🎯 MILESTONE 4 - DEMO MODE ACTIVATED!')
            print('===================================================')
            #print('📅 DEMO SCHEDULE:')
            #print('   ⚡ EVERY 1 MINUTE - Test Reminders')
            print('   🕘 9:00 AM - Morning Reminders (Production)')
            print('   🕑 2:00 PM - Afternoon Reminders (Production)') 
            print('   🕖 7:00 PM - Evening Reminders (Production)')
            print('===================================================')
            print('📧 Emails will send at scheduled times (9AM, 2PM, 7PM)')
            print('🛑 Press Ctrl+C to stop the scheduler\n')
        
        def get_course_progress(self, enrollment):
            """Get progress from available fields"""
            return getattr(enrollment, 'completion_percentage', 
                          getattr(enrollment, 'course_progress', 
                                 getattr(enrollment, 'progress', 0)))
        
        def send_reminders_to_all_students(self, time_of_day):
            """Send reminders to all students - ONLY INCOMPLETE COURSES"""
            print(f'⏰ {datetime.now().strftime("%H:%M:%S")} - Sending {time_of_day.upper()} reminders...')
            
            try:
                # Get ONLY students
                students = BaseUser.objects.filter(user_type='student')
                student_count = students.count()
                
                print(f'📧 Found {student_count} registered STUDENTS')
                
                email_count = 0
                errors = 0
                skipped_completed = 0
                
                for student in students:
                    if student.email:
                        try:
                            # Get student's courses
                            student_courses = StudentCourse.objects.filter(student=student)
                            
                            if student_courses.exists():
                                incomplete_courses = []
                                
                                # Filter out completed courses
                                for enrollment in student_courses:
                                    progress = self.get_course_progress(enrollment)
                                    
                                    # Only include courses that are NOT completed (progress < 100%)
                                    if progress < 100:
                                        incomplete_courses.append(enrollment)
                                    else:
                                        skipped_completed += 1
                                        print(f'   ⏭️  Skipping completed course: {enrollment.course.course_name} ({progress}%)')
                                
                                if incomplete_courses:
                                    print(f'   📚 {student.email} has {len(incomplete_courses)} incomplete courses')
                                    
                                    for enrollment in incomplete_courses:
                                        try:
                                            progress = self.get_course_progress(enrollment)
                                            print(f'      🎯 {enrollment.course.course_name} - {progress}% complete')
                                            
                                            # Send email only for incomplete courses
                                            success = send_course_reminder_email(student, enrollment,time_of_day)
                                            
                                            if success:
                                                email_count += 1
                                                print(f'      ✅ Email sent for {enrollment.course.course_name}')
                                            else:
                                                errors += 1
                                                print(f'      ❌ Failed to send email')
                                                
                                        except Exception as e:
                                            errors += 1
                                            print(f'      ❌ Email error: {e}')
                                else:
                                    print(f'   📭 No incomplete courses for {student.email}')
                            else:
                                print(f'⚠️ No courses found for {student.email}')
                                
                        except Exception as e:
                            errors += 1
                            print(f'❌ Error processing {student.email}: {e}')
                
                # Summary report
                print(f'\n🎯 {time_of_day.upper()} COMPLETED:')
                print(f'   ✅ {email_count} emails sent successfully')
                print(f'   ⏭️  {skipped_completed} completed courses skipped')
                print(f'   ❌ {errors} errors')
                #print(f'   ⏰ Next reminder in 1 minute...\n')
                print('=' * 50)
                    
            except Exception as e:
                print(f'❌ ERROR in {time_of_day} reminders: {e}')

    # Initialize the scheduler
    scheduler = EmailScheduler()

    # Create APScheduler instance
    aps_scheduler = BackgroundScheduler()

    # 🎪 DEMO MODE: Send emails EVERY 1 MINUTE
    #aps_scheduler.add_job(
    #    lambda: scheduler.send_reminders_to_all_students('DEMO'),
     #   IntervalTrigger(minutes=1),  # EVERY 1 MINUTE
      #  id='demo_reminder'
    #)

    # Production schedules (keep for reference)
    aps_scheduler.add_job(
        lambda: scheduler.send_reminders_to_all_students('morning'),
        CronTrigger(hour=9, minute=15),  # 9:00 AM
        id='morning_reminder'
    )

    aps_scheduler.add_job(
        lambda: scheduler.send_reminders_to_all_students('afternoon'),
        CronTrigger(hour=2, minute=0),  # 2:00 PM
        id='afternoon_reminder'
    )

    aps_scheduler.add_job(
        lambda: scheduler.send_reminders_to_all_students('evening'),
        CronTrigger(hour=19, minute=0),  # 7:00 PM
        id='evening_reminder'
    )

    # Start the scheduler
    aps_scheduler.start()

    print("\n⏰ PRODUCTION SCHEDULER STARTED!")
    print("📧 Emails will send at:")
    print("   🕘 9:00 AM - Morning")
    print("   🕑 2:00 PM - Afternoon") 
    print("   🕖 7:00 PM - Evening")
    print("🛑 Press Ctrl+C to stop the scheduler\n")

    # Send first batch immediately
    #scheduler.send_reminders_to_all_students('DEMO')

    # Keep the scheduler running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('🛑 Stopping demo...')
        aps_scheduler.shutdown()

except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()