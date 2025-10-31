# management/commands/send_daily_quiz_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from datetime import timedelta
from ui.models import Quiz, BaseUser, StudentCourse, QuizAttempt, QuizReminder
from ui.services import get_time_greeting, get_quiz_motivation
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send daily automatic quiz reminders to students with ALL pending quizzes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test mode - show what would be sent without actually sending emails'
        )
        parser.add_argument(
            '--include-expired',
            action='store_true',
            help='Include expired quizzes in reminders'
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🤖 Starting DAILY AUTOMATIC Quiz Reminder System...")
        
        test_mode = options['test']
        include_expired = options['include_expired']
        
        if test_mode:
            self.stdout.write(self.style.WARNING("🔍 TEST MODE - No emails will be actually sent"))
        
        if include_expired:
            self.stdout.write(self.style.WARNING("📅 INCLUDING EXPIRED QUIZZES"))
        
        try:
            results = self.send_daily_quiz_reminders(test_mode, include_expired)
            self.print_results(results, test_mode)
            
        except Exception as e:
            logger.error(f"Error in daily quiz reminder command: {str(e)}")
            self.stdout.write(self.style.ERROR(f"❌ Error: {str(e)}"))
    
    def send_daily_quiz_reminders(self, test_mode=False, include_expired=False):
        """Send daily automatic reminders for ALL pending quizzes"""
        
        now = timezone.now()
        
        # Get ALL quizzes (including expired if requested)
        if include_expired:
            quizzes = Quiz.objects.all().select_related('course')
        else:
            quizzes = Quiz.objects.filter(
                due_date__gte=now
            ).select_related('course')
        
        results = {
            'total_quizzes': quizzes.count(),
            'total_reminders_sent': 0,
            'quizzes_processed': 0,
            'students_notified': 0,
            'errors': [],
            'quiz_details': []
        }
        
        for quiz in quizzes:
            try:
                quiz_result = self.process_quiz_daily_reminder(quiz, test_mode, include_expired)
                results['quizzes_processed'] += 1
                results['total_reminders_sent'] += quiz_result['emails_sent']
                results['students_notified'] += quiz_result['students_notified']
                results['quiz_details'].append(quiz_result)
                
            except Exception as e:
                error_msg = f"Error processing quiz {quiz.id}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        return results
    
    def process_quiz_daily_reminder(self, quiz, test_mode=False, include_expired=False):
        """Process daily automatic reminder for a single quiz"""
        
        now = timezone.now()
        is_expired = quiz.due_date and quiz.due_date < now
        
        # Get all enrolled students
        enrolled_students = BaseUser.objects.filter(
            user_type='student',
            studentcourse__course=quiz.course
        ).distinct()
        
        # Get students who have attempted this quiz
        students_with_attempts = QuizAttempt.objects.filter(
            quiz=quiz,
            is_completed=True
        ).values_list('student_id', flat=True)
        
        # Exclude students who have already attempted
        students_to_notify = enrolled_students.exclude(id__in=students_with_attempts)
        
        students_notified = 0
        emails_sent = 0
        
        quiz_result = {
            'quiz_id': quiz.id,
            'quiz_title': quiz.title,
            'course_name': quiz.course.course_name,
            'is_expired': is_expired,
            'students_notified': 0,
            'emails_sent': 0,
            'student_details': []
        }
        
        for student in students_to_notify:
            try:
                # Get student's course progress
                student_course = StudentCourse.objects.get(
                    student=student,
                    course=quiz.course
                )
                course_progress = student_course.course_progress
                
                # Calculate days remaining (negative if expired)
                if quiz.due_date:
                    days_remaining = (quiz.due_date - now).days
                else:
                    days_remaining = None
                
                # Determine urgency level and message
                urgency_info = self.get_urgency_level(days_remaining, is_expired)
                
                if not test_mode:
                    # Send actual email
                    email_sent = self.send_quiz_reminder_email(student, quiz, course_progress, urgency_info, is_expired)
                    
                    if email_sent:
                        emails_sent += 1
                        
                        # Create reminder record
                        QuizReminder.objects.create(
                            quiz=quiz,
                            student=student,
                            reminder_type='automatic_daily'
                        )
                else:
                    # Test mode - just count
                    emails_sent += 1
                
                students_notified += 1
                
                quiz_result['student_details'].append({
                    'student_id': student.id,
                    'student_name': student.get_full_name() or student.username,
                    'email': student.email,
                    'course_progress': course_progress,
                    'days_remaining': days_remaining,
                    'is_expired': is_expired,
                    'urgency_level': urgency_info['level'],
                    'email_sent': not test_mode
                })
                
            except StudentCourse.DoesNotExist:
                continue
            except Exception as e:
                error_msg = f"Error processing student {student.id}: {str(e)}"
                logger.error(error_msg)
                quiz_result['student_details'].append({
                    'student_id': student.id,
                    'error': error_msg
                })
        
        quiz_result.update({
            'students_notified': students_notified,
            'emails_sent': emails_sent
        })
        
        return quiz_result
    
    def get_urgency_level(self, days_remaining, is_expired):
        """Determine urgency level based on days remaining and expiration status"""
        if is_expired:
            return {
                'level': '📅 EXPIRED - STILL PENDING',
                'subject_prefix': '📅 Overdue Quiz: ',
                'custom_message': 'This quiz is past due but you can still attempt it for practice!'
            }
        elif days_remaining is None:
            return {
                'level': '📝 NO DUE DATE',
                'subject_prefix': '📝 Quiz Available: ',
                'custom_message': 'Take this quiz at your convenience to test your knowledge!'
            }
        elif days_remaining <= 0:
            return {
                'level': '🚨 DUE TODAY',
                'subject_prefix': '🚨 Due TODAY: ',
                'custom_message': 'QUIZ DUE TODAY! Please attempt it before the deadline.'
            }
        elif days_remaining <= 1:
            return {
                'level': '🚨 URGENT',
                'subject_prefix': '🚨 URGENT: Due Tomorrow - ',
                'custom_message': 'QUIZ DUE TOMORROW! Please attempt it today.'
            }
        elif days_remaining <= 3:
            return {
                'level': '⏰ HIGH PRIORITY',
                'subject_prefix': '⏰ Due Soon: ',
                'custom_message': f'Quiz due in {days_remaining} days. Plan your attempt soon!'
            }
        elif days_remaining <= 7:
            return {
                'level': '📝 REMINDER',
                'subject_prefix': '📝 Upcoming Quiz: ',
                'custom_message': f'Quiz due in {days_remaining} days. Good time to start preparing!'
            }
        else:
            return {
                'level': '📚 AVAILABLE',
                'subject_prefix': '📚 Quiz Available: ',
                'custom_message': f'You have a quiz available. Due in {days_remaining} days.'
            }
    
    def send_quiz_reminder_email(self, student, quiz, course_progress, urgency_info, is_expired):
        """Send actual quiz reminder email"""
        try:
            # Prepare email content
            time_greeting = get_time_greeting()
            quiz_motivation = get_quiz_motivation(course_progress)
            
            # Format due date display
            if quiz.due_date:
                due_date_display = quiz.due_date.strftime("%B %d, %Y at %I:%M %p")
                if is_expired:
                    due_date_display = f"⏰ EXPIRED: {due_date_display}"
                else:
                    days_remaining = (quiz.due_date - timezone.now()).days
                    if days_remaining >= 0:
                        due_date_display = f"📅 Due: {due_date_display} ({abs(days_remaining)} days {'remaining' if days_remaining > 0 else 'TODAY'})"
            else:
                due_date_display = "No due date - Take anytime"
            
            context = {
                'time_greeting': time_greeting,
                'quiz_motivation': quiz_motivation,
                'student_name': student.first_name or student.username,
                'quiz_title': quiz.title,
                'course_name': quiz.course.course_name,
                'course_progress': course_progress,
                'due_date': due_date_display,
                'quiz_url': f"{settings.SITE_URL}/student/quiz/{quiz.id}/take/",
                'custom_message': urgency_info['custom_message'],
                'settings': {'SITE_URL': settings.SITE_URL},
                'urgency_level': urgency_info['level'],
                'is_expired': is_expired,
                'quiz_has_due_date': quiz.due_date is not None
            }
            
            # Render email template
            email_html = render_to_string('ai_quiz_reminder_email.html', context)
            plain_message = strip_tags(email_html)
            
            # SEND ACTUAL EMAIL
            send_mail(
                subject=f"{urgency_info['subject_prefix']}{quiz.title}",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                html_message=email_html,
                fail_silently=False,
            )
            
            status = "EXPIRED" if is_expired else "PENDING"
            logger.info(f"✅ DAILY AUTOMATIC: {status} quiz reminder sent to {student.email} for '{quiz.title}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending email to {student.email}: {str(e)}")
            return False
    
    def print_results(self, results, test_mode=False):
        """Print daily automatic reminder results"""
        
        if test_mode:
            self.stdout.write(self.style.WARNING("🔍 TEST MODE - No emails were actually sent"))
        
        self.stdout.write(self.style.SUCCESS(f"✅ DAILY AUTOMATIC Quiz Reminder System Completed!"))
        self.stdout.write(f"📊 Summary:")
        self.stdout.write(f"   • Total Quizzes Checked: {results['total_quizzes']}")
        self.stdout.write(f"   • Quizzes Processed: {results['quizzes_processed']}")
        self.stdout.write(f"   • Students Notified: {results['students_notified']}")
        self.stdout.write(f"   • Emails {'Would Be Sent' if test_mode else 'Sent'}: {results['total_reminders_sent']}")
        
        if results['errors']:
            self.stdout.write(self.style.ERROR(f"❌ Errors: {len(results['errors'])}"))
            for error in results['errors'][:3]:
                self.stdout.write(f"   - {error}")
        
        # Show details for each quiz
        expired_count = 0
        active_count = 0
        
        for detail in results['quiz_details']:
            if detail['students_notified'] > 0:
                status = "📅 EXPIRED" if detail['is_expired'] else "✅ ACTIVE"
                if detail['is_expired']:
                    expired_count += 1
                else:
                    active_count += 1
                    
                self.stdout.write(f"\n{status} Quiz: {detail['quiz_title']}")
                self.stdout.write(f"   Course: {detail['course_name']}")
                self.stdout.write(f"   Students Notified: {detail['students_notified']}")
                self.stdout.write(f"   Emails Sent: {detail['emails_sent']}")
        
        # Show summary by status
        if expired_count > 0 or active_count > 0:
            self.stdout.write(f"\n📈 Breakdown:")
            self.stdout.write(f"   • Active Quizzes: {active_count}")
            self.stdout.write(f"   • Expired Quizzes: {expired_count}")