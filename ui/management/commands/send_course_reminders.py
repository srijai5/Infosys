# ui/management/commands/send_course_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from ui.services import NotificationService
from ui.models import BaseUser, StudentCourse
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send course reminders based on time of day and student preferences'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force send reminders regardless of time',
        )
        parser.add_argument(
            '--student',
            type=str,
            help='Send reminders only for specific student (username)',
        )
        parser.add_argument(
            '--course',
            type=int,
            help='Send reminders only for specific course ID',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(f'🚀 Starting course reminders at {timezone.now()}...')
        
        current_period = NotificationService.get_current_reminder_period()
        self.stdout.write(f'📅 Current time period: {current_period or "Outside reminder hours"}')
        
        if not current_period and not options['force']:
            self.stdout.write(
                self.style.WARNING('⏰ Outside reminder hours. Use --force to send anyway.')
            )
            return
        
        # Filter students if specified
        students = BaseUser.objects.filter(user_type='student', is_active=True)
        if options['student']:
            students = students.filter(username=options['student'])
            self.stdout.write(f'🎯 Targeting student: {options["student"]}')
        
        results = {
            'total_students': students.count(),
            'emails_sent': 0,
            'alerts_created': 0,
            'errors': []
        }
        
        for student in students:
            try:
                # Check if we should send reminders for this student
                if not options['force'] and not NotificationService.should_send_reminder(student):
                    continue
                
                # Get student's courses
                student_courses = StudentCourse.objects.filter(
                    student=student,
                    status='in_progress',
                    completed=False
                ).select_related('course')
                
                if options['course']:
                    student_courses = student_courses.filter(course_id=options['course'])
                
                courses_to_remind = []
                courses_with_quizzes = []
                high_completion_courses = []
                
                for sc in student_courses:
                    if sc.needs_reminder:
                        courses_to_remind.append(sc)
                    if sc.high_completion_alert:
                        high_completion_courses.append(sc)
                    if sc.has_pending_quiz:
                        courses_with_quizzes.append(sc)
                
                # Send course reminders
                for course_sc in courses_to_remind:
                    try:
                        pref = student.notification_preferences
                        if pref.email_notifications:
                            from ui.utils import send_course_reminder_email
                            success = send_course_reminder_email(student, course_sc)
                            if success:
                                results['emails_sent'] += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f'✅ Course reminder sent to {student.email}')
                                )
                    except Exception as e:
                        error_msg = f"Course reminder error for {student.email}: {str(e)}"
                        results['errors'].append(error_msg)
                        self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
                
                # Send quiz reminders
                for quiz_course in courses_with_quizzes:
                    try:
                        pref = student.notification_preferences
                        if pref.email_notifications:
                            from ui.utils import send_quiz_reminder_email
                            success = send_quiz_reminder_email(student, quiz_course)
                            if success:
                                results['emails_sent'] += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f'✅ Quiz reminder sent to {student.email}')
                                )
                    except Exception as e:
                        error_msg = f"Quiz reminder error for {student.email}: {str(e)}"
                        results['errors'].append(error_msg)
                        self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
                
                # Create dashboard alerts
                for high_course in high_completion_courses:
                    try:
                        pref = student.notification_preferences
                        if pref.dashboard_alerts:
                            alert_created = NotificationService.create_high_completion_alert(student, high_course)
                            if alert_created:
                                results['alerts_created'] += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f'🎯 High completion alert created for {student.username}')
                                )
                    except Exception as e:
                        error_msg = f"Alert creation error for {student.username}: {str(e)}"
                        results['errors'].append(error_msg)
                        self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
                        
            except Exception as e:
                error_msg = f"Student processing error for {student.username}: {str(e)}"
                results['errors'].append(error_msg)
                self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(
            f"🎊 REMINDER SUMMARY:\n"
            f"• Students processed: {results['total_students']}\n"
            f"• Emails sent: {results['emails_sent']}\n"
            f"• Alerts created: {results['alerts_created']}\n"
            f"• Errors: {len(results['errors'])}"
        ))
        
        if results['errors']:
            self.stdout.write(self.style.WARNING("\n📋 Errors encountered:"))
            for error in results['errors']:
                self.stdout.write(f"  • {error}")