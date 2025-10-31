from django.core.mail import send_mail
from django.conf import settings

def send_reminder_email(time_of_day):
    """Send reminder email - this will be called by the scheduler"""
    try:
        send_mail(
            subject=f'📚 {time_of_day.capitalize()} Reminder: Continue Your Courses',
            message=f'Hello! This is your {time_of_day} reminder to continue your courses on StudyTrack.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['nvasanthi2005@gmail.com'],
            fail_silently=False,
        )
        print(f"✅ {time_of_day.capitalize()} email sent to nvasanthi2005@gmail.com")
        return f"{time_of_day.capitalize()} reminder sent successfully"
    except Exception as e:
        print(f"❌ Error sending {time_of_day} email: {str(e)}")
        return f"Error: {str(e)}"