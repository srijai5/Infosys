import os
import django
import sys

sys.path.append('.')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infosys.settings')

try:
    django.setup()
    
    from django.core.mail import send_mail
    from django.conf import settings
    
    print('Testing email system...')
    
    send_mail(
        subject='Test Email from StudyTrack',
        message='This is a test email to verify the system works.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=['nvasanthi2005@gmail.com'],
        fail_silently=False,
    )
    print('SUCCESS: Test email sent successfully!')
    print('Check nvasanthi2005@gmail.com')
    
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()