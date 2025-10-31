# ui/management/commands/debug_email.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from ui.models import BaseUser, StudentCourse

class Command(BaseCommand):
    help = 'Test email configuration and send test emails'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Send test email to specific address',
        )
        parser.add_argument(
            '--student',
            type=str,
            help='Send test email to student',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('📧 DEBUG EMAIL CONFIGURATION')
        self.stdout.write('=' * 40)
        
        # Check email settings
        self.stdout.write(f'📋 Email Settings:')
        self.stdout.write(f'  • EMAIL_HOST: {getattr(settings, "EMAIL_HOST", "Not set")}')
        self.stdout.write(f'  • EMAIL_PORT: {getattr(settings, "EMAIL_PORT", "Not set")}')
        self.stdout.write(f'  • EMAIL_USE_TLS: {getattr(settings, "EMAIL_USE_TLS", "Not set")}')
        self.stdout.write(f'  • DEFAULT_FROM_EMAIL: {getattr(settings, "DEFAULT_FROM_EMAIL", "Not set")}')
        
        # Determine recipient
        recipient_email = None
        if options['email']:
            recipient_email = options['email']
        elif options['student']:
            try:
                student = BaseUser.objects.get(username=options['student'], user_type='student')
                recipient_email = student.email
            except BaseUser.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Student not found: {options["student"]}'))
                return
        
        if not recipient_email:
            self.stdout.write(self.style.WARNING('⚠️ No recipient specified. Use --email or --student'))
            return
        
        # Send test email
        self.stdout.write(f'\n📤 Sending test email to: {recipient_email}')
        
        try:
            send_mail(
                subject='🎯 Test Email - Learning Platform',
                message='This is a test email from your learning platform notification system.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS('✅ Test email sent successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to send test email: {str(e)}'))