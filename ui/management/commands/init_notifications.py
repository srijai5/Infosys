# ui/management/commands/init_notifications.py
from django.core.management.base import BaseCommand
from django.core.management import call_command
from ui.models import BaseUser, NotificationPreference

class Command(BaseCommand):
    help = 'Initialize the complete notification system'
    
    def handle(self, *args, **options):
        self.stdout.write('🚀 INITIALIZING NOTIFICATION SYSTEM')
        self.stdout.write('=' * 50)
        
        # Step 1: Setup notification preferences
        self.stdout.write('\n📋 Step 1: Setting up notification preferences...')
        call_command('setup_notification_preferences')
        
        # Step 2: Test email configuration
        self.stdout.write('\n📧 Step 2: Testing email configuration...')
        call_command('debug_email', '--student', 'admin')
        
        # Step 3: Test reminder logic
        self.stdout.write('\n🔍 Step 3: Testing reminder logic...')
        call_command('debug_reminders')
        
        # Step 4: Send test reminders
        self.stdout.write('\n📤 Step 4: Sending test reminders...')
        call_command('send_course_reminders', '--force', '--student', 'admin')
        
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('🎉 Notification system initialized successfully!'))
        self.stdout.write('\n📝 Next steps:')
        self.stdout.write('  1. Setup cron jobs for automated reminders')
        self.stdout.write('  2. Test with actual students')
        self.stdout.write('  3. Monitor email logs in admin panel')