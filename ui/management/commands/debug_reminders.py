# ui/management/commands/debug_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from ui.models import BaseUser, StudentCourse, NotificationPreference
from ui.services import NotificationService

class Command(BaseCommand):
    help = 'Debug and test reminder logic without sending emails'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--student',
            type=str,
            help='Debug specific student',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('🔍 DEBUG REMINDER SYSTEM')
        self.stdout.write('=' * 50)
        
        # Current time analysis
        now = timezone.now()
        current_period = NotificationService.get_current_reminder_period()
        self.stdout.write(f'🕒 Current time: {now}')
        self.stdout.write(f'📅 Reminder period: {current_period or "Outside hours"}')
        
        # Student analysis
        students = BaseUser.objects.filter(user_type='student', is_active=True)
        if options['student']:
            students = students.filter(username=options['student'])
        
        self.stdout.write(f'\n👥 Analyzing {students.count()} students:')
        self.stdout.write('-' * 30)
        
        for student in students:
            self.stdout.write(f'\n🎓 Student: {student.username} ({student.email})')
            
            # Check preferences
            try:
                pref = student.notification_preferences
                self.stdout.write(f'  📧 Email notifications: {pref.email_notifications}')
                self.stdout.write(f'  🎯 Dashboard alerts: {pref.dashboard_alerts}')
                self.stdout.write(f'  ⏰ Frequency: {pref.reminder_frequency}')
                self.stdout.write(f'  🔔 Should send now: {NotificationService.should_send_reminder(student)}')
            except NotificationPreference.DoesNotExist:
                self.stdout.write('  ❌ No notification preferences found')
                continue
            
            # Check courses
            student_courses = StudentCourse.objects.filter(
                student=student,
                status='in_progress',
                completed=False
            ).select_related('course')
            
            self.stdout.write(f'  📚 Active courses: {student_courses.count()}')
            
            for sc in student_courses:
                progress = sc.course_progress
                self.stdout.write(f'    • {sc.course.course_name}: {progress}%')
                self.stdout.write(f'      Needs reminder: {sc.needs_reminder}')
                self.stdout.write(f'      High completion: {sc.high_completion_alert}')
                self.stdout.write(f'      Has pending quiz: {sc.has_pending_quiz}')
        
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('✅ Debug completed')