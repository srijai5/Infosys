# ui/management/commands/setup_notification_preferences.py
from django.core.management.base import BaseCommand
from ui.models import BaseUser, NotificationPreference

class Command(BaseCommand):
    help = 'Setup default notification preferences for all students'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all existing preferences to defaults',
        )
    
    def handle(self, *args, **options):
        students = BaseUser.objects.filter(user_type='student', is_active=True)
        
        self.stdout.write(f'👥 Setting up notification preferences for {students.count()} students...')
        
        created_count = 0
        updated_count = 0
        
        for student in students:
            try:
                if options['reset']:
                    # Delete existing and create new
                    NotificationPreference.objects.filter(student=student).delete()
                    NotificationPreference.objects.create(student=student)
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Reset preferences for {student.username}')
                    )
                else:
                    # Create only if doesn't exist
                    pref, created = NotificationPreference.objects.get_or_create(
                        student=student,
                        defaults={
                            'email_notifications': True,
                            'dashboard_alerts': True,
                            'reminder_frequency': 'multiple'
                        }
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Created preferences for {student.username}')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️ Preferences already exist for {student.username}')
                        )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error for {student.username}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Setup completed!\n'
                f'• New preferences created: {created_count}\n'
                f'• Preferences reset: {updated_count if options["reset"] else "N/A"}'
            )
        )