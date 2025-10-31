# management/commands/test_email_setup.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from ui.models import Course, StudentCourse, NotificationPreference

class Command(BaseCommand):
    help = 'Create test student and course for email testing'
    
    def handle(self, *args, **options):
        User = get_user_model()
        
        # Create or get test student with YOUR email
        student, created = User.objects.get_or_create(
            username='teststudent',
            defaults={
                'email': 'your-email@gmail.com',  # REPLACE WITH YOUR EMAIL
                'first_name': 'Test',
                'last_name': 'Student',
                'password': 'testpassword123'
            }
        )
        
        # Create or get a test course
        course, created = Course.objects.get_or_create(
            course_name='Python Programming',
            defaults={
                'description': 'Test course for email notifications',
                'duration_weeks': 4
            }
        )
        
        # Enroll student in course
        student_course, created = StudentCourse.objects.get_or_create(
            student=student,
            course=course,
            defaults={
                'status': 'in_progress'
            }
        )
        
        # Ensure notification preferences exist
        NotificationPreference.objects.get_or_create(student=student)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Test setup complete! Student: {student.username}, Course: {course.course_name}'
            )
        )