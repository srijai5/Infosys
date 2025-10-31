from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta
from ui.models import Quiz, BaseUser, StudentCourse, QuizReminder, QuizAttempt
from ui.services import get_time_greeting, get_quiz_motivation
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# TASK 1: COURSE REMINDERS (Your existing code)
# ============================================================================
@shared_task
def send_morning_reminders():
    """Send morning reminders"""
    logger.info("🕘 Sending morning reminders...")
    send_scheduled_reminders("morning")
    return "Morning reminders sent"

@shared_task
def send_afternoon_reminders():
    """Send afternoon reminders"""
    logger.info("🕑 Sending afternoon reminders...")
    send_scheduled_reminders("afternoon")
    return "Afternoon reminders sent"

@shared_task
def send_evening_reminders():
    """Send evening reminders"""
    logger.info("🕖 Sending evening reminders...")
    send_scheduled_reminders("evening")
    return "Evening reminders sent"

def send_scheduled_reminders(time_of_day):
    """Send actual email using your email configuration"""
    try:
        # This uses your existing email settings from settings.py
        send_mail(
            subject=f'📚 {time_of_day.capitalize()} Reminder: Continue Your Courses',
            message=f'Hello! This is your {time_of_day} reminder to continue your courses on StudyTrack.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['nvasanthi2005@gmail.com'],  # Your test email
            fail_silently=False,
        )
        logger.info(f"✅ {time_of_day.capitalize()} email sent to nvasanthi2005@gmail.com")
    except Exception as e:
        logger.error(f"❌ Error sending {time_of_day} email: {str(e)}")

# ============================================================================
# TASK 2: AUTOMATIC QUIZ REMINDERS
# ============================================================================
@shared_task
def send_quiz_creation_reminders_task(quiz_id):
    """AUTOMATIC: Send reminders when a new quiz is created"""
    try:
        quiz = Quiz.objects.get(id=quiz_id)
        logger.info(f"🚀 AUTOMATIC: Sending quiz creation reminders for '{quiz.title}'")
        
        # Get all students enrolled in the course
        enrolled_students = BaseUser.objects.filter(
            user_type='student',
            studentcourse__course=quiz.course
        ).distinct()
        
        reminders_sent = 0
        
        for student in enrolled_students:
            try:
                # Get student's course progress
                student_course = StudentCourse.objects.get(
                    student=student,
                    course=quiz.course
                )
                course_progress = student_course.course_progress
                
                # Prepare email content
                time_greeting = get_time_greeting()
                quiz_motivation = get_quiz_motivation(course_progress)
                
                context = {
                    'time_greeting': time_greeting,
                    'quiz_motivation': quiz_motivation,
                    'student_name': student.first_name or student.username,
                    'quiz_title': quiz.title,
                    'course_name': quiz.course.course_name,
                    'course_progress': course_progress,
                    'due_date': quiz.due_date.strftime("%B %d, %Y at %I:%M %p") if quiz.due_date else "No due date",
                    'quiz_url': f"{settings.SITE_URL}/student/quiz/{quiz.id}/take/",
                    'custom_message': "🎯 New quiz available! Check it out now.",
                    'settings': {'SITE_URL': settings.SITE_URL}
                }
                
                # Render email template
                email_html = render_to_string('ai_quiz_reminder_email.html', context)
                plain_message = strip_tags(email_html)
                
                # SEND ACTUAL EMAIL AUTOMATICALLY
                send_mail(
                    subject=f"📝 New Quiz: {quiz.title}",
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[student.email],
                    html_message=email_html,
                    fail_silently=False,
                )
                
                # Create reminder record
                QuizReminder.objects.create(
                    quiz=quiz,
                    student=student,
                    reminder_type='automatic_creation'
                )
                
                reminders_sent += 1
                logger.info(f"✅ AUTOMATIC: Quiz creation reminder sent to {student.email}")
                
            except StudentCourse.DoesNotExist:
                logger.warning(f"Student {student.username} not enrolled in course {quiz.course.course_name}")
                continue
            except Exception as e:
                logger.error(f"❌ Error sending to {student.email}: {str(e)}")
                continue
        
        logger.info(f"✅ AUTOMATIC: Sent {reminders_sent} quiz creation reminders for '{quiz.title}'")
        return reminders_sent
        
    except Quiz.DoesNotExist:
        logger.error(f"❌ Quiz with id {quiz_id} not found")
        return 0
    except Exception as e:
        logger.error(f"❌ Error in automatic quiz creation task: {str(e)}")
        return 0

@shared_task
def send_daily_quiz_reminders_task():
    """AUTOMATIC: Send daily reminders for pending quizzes"""
    try:
        now = timezone.now()
        
        # Get active quizzes (due in future)
        active_quizzes = Quiz.objects.filter(
            due_date__gte=now
        ).select_related('course')
        
        total_reminders_sent = 0
        
        for quiz in active_quizzes:
            try:
                # Get students who haven't attempted this quiz
                enrolled_students = BaseUser.objects.filter(
                    user_type='student',
                    studentcourse__course=quiz.course
                ).exclude(
                    quizattempt__quiz=quiz,
                    quizattempt__is_completed=True
                ).distinct()
                
                quiz_reminders_sent = 0
                
                for student in enrolled_students:
                    try:
                        # Get student's course progress
                        student_course = StudentCourse.objects.get(
                            student=student,
                            course=quiz.course
                        )
                        course_progress = student_course.course_progress
                        
                        # Calculate days remaining
                        days_remaining = (quiz.due_date - now).days
                        
                        # Determine urgency level
                        if days_remaining <= 1:
                            urgency_level = "🚨 URGENT"
                            custom_message = f"Quiz due TOMORROW! Please attempt it now."
                        elif days_remaining <= 3:
                            urgency_level = "⏰ HIGH PRIORITY"
                            custom_message = f"Quiz due in {days_remaining} days. Don't wait until the last minute!"
                        elif days_remaining <= 7:
                            urgency_level = "📝 REMINDER"
                            custom_message = f"Quiz due in {days_remaining} days. Plan your attempt soon!"
                        else:
                            urgency_level = "📚 PLANNING"
                            custom_message = f"You have a quiz coming up. Start preparing early!"
                        
                        # Prepare email content
                        time_greeting = get_time_greeting()
                        quiz_motivation = get_quiz_motivation(course_progress)
                        
                        context = {
                            'time_greeting': time_greeting,
                            'quiz_motivation': quiz_motivation,
                            'student_name': student.first_name or student.username,
                            'quiz_title': quiz.title,
                            'course_name': quiz.course.course_name,
                            'course_progress': course_progress,
                            'due_date': quiz.due_date.strftime("%B %d, %Y at %I:%M %p"),
                            'quiz_url': f"{settings.SITE_URL}/student/quiz/{quiz.id}/take/",
                            'custom_message': custom_message,
                            'settings': {'SITE_URL': settings.SITE_URL},
                            'urgency_level': urgency_level,
                            'days_remaining': days_remaining
                        }
                        
                        # Render email template
                        email_html = render_to_string('ai_quiz_reminder_email.html', context)
                        plain_message = strip_tags(email_html)
                        
                        # SEND ACTUAL EMAIL AUTOMATICALLY
                        send_mail(
                            subject=f"{urgency_level}: {quiz.title} - Due in {days_remaining} days",
                            message=plain_message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[student.email],
                            html_message=email_html,
                            fail_silently=False,
                        )
                        
                        # Create reminder record
                        QuizReminder.objects.create(
                            quiz=quiz,
                            student=student,
                            reminder_type='automatic_daily'
                        )
                        
                        quiz_reminders_sent += 1
                        total_reminders_sent += 1
                        
                        logger.info(f"✅ DAILY AUTOMATIC: Quiz reminder sent to {student.email} for '{quiz.title}'")
                        
                    except StudentCourse.DoesNotExist:
                        continue
                    except Exception as e:
                        logger.error(f"❌ Error sending daily reminder to {student.email}: {str(e)}")
                        continue
                
                if quiz_reminders_sent > 0:
                    logger.info(f"📊 DAILY AUTOMATIC: Sent {quiz_reminders_sent} reminders for '{quiz.title}'")
                    
            except Exception as e:
                logger.error(f"❌ Error processing quiz {quiz.id}: {str(e)}")
                continue
        
        logger.info(f"🎯 DAILY AUTOMATIC: Completed - Sent {total_reminders_sent} total quiz reminders")
        return total_reminders_sent
        
    except Exception as e:
        logger.error(f"❌ Error in daily quiz reminders task: {str(e)}")
        return 0

@shared_task
def send_weekly_quiz_summary_task():
    """AUTOMATIC: Send weekly quiz summary to all students"""
    try:
        now = timezone.now()
        week_start = now - timedelta(days=7)
        
        students = BaseUser.objects.filter(user_type='student')
        summaries_sent = 0
        
        for student in students:
            try:
                # Get student's pending quizzes
                enrolled_courses = StudentCourse.objects.filter(
                    student=student
                ).values_list('course_id', flat=True)
                
                pending_quizzes = Quiz.objects.filter(
                    course_id__in=enrolled_courses,
                    due_date__gte=now
                ).exclude(
                    quizattempt__student=student,
                    quizattempt__is_completed=True
                )
                
                if pending_quizzes.exists():
                    # Prepare weekly summary email
                    context = {
                        'student_name': student.first_name or student.username,
                        'pending_quizzes': pending_quizzes,
                        'week_start': week_start.strftime("%B %d"),
                        'settings': {'SITE_URL': settings.SITE_URL}
                    }
                    
                    email_html = render_to_string('weekly_quiz_summary_email.html', context)
                    plain_message = strip_tags(email_html)
                    
                    send_mail(
                        subject="📊 Your Weekly Quiz Summary",
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[student.email],
                        html_message=email_html,
                        fail_silently=False,
                    )
                    
                    summaries_sent += 1
                    logger.info(f"✅ WEEKLY SUMMARY: Sent to {student.email}")
                    
            except Exception as e:
                logger.error(f"❌ Error sending weekly summary to {student.email}: {str(e)}")
                continue
        
        logger.info(f"📊 WEEKLY SUMMARY: Sent {summaries_sent} weekly quiz summaries")
        return summaries_sent
        
    except Exception as e:
        logger.error(f"❌ Error in weekly quiz summary task: {str(e)}")
        return 0