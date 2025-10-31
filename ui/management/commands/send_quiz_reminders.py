# management/commands/send_quiz_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from ui.models import BaseUser, Quiz, QuizAttempt, StudentCourse, QuizReminder, DashboardAlert
from ui.services import send_ai_quiz_reminder
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send quiz attempt reminders to students with pending quizzes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reminder-type',
            type=str,
            choices=['pending', 'all', 'custom'],
            default='pending',
            help='Type of reminders to send: pending (only students who haven\'t attempted), all (all enrolled students), custom (custom selection)'
        )
        parser.add_argument(
            '--quiz-id',
            type=int,
            help='Specific quiz ID to send reminders for (optional)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate sending without actually sending emails'
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🚀 Starting Quiz Reminder System...")
        
        reminder_type = options['reminder_type']
        quiz_id = options['quiz_id']
        dry_run = options['dry_run']
        
        try:
            results = self.send_quiz_reminders(reminder_type, quiz_id, dry_run)
            self.print_results(results, dry_run)
            
        except Exception as e:
            logger.error(f"Error in quiz reminder command: {str(e)}")
            self.stdout.write(self.style.ERROR(f"❌ Error: {str(e)}"))
    
    def send_quiz_reminders(self, reminder_type='pending', quiz_id=None, dry_run=False):
        """Send quiz reminders based on type and filters"""
        
        # Get active quizzes (not expired)
        now = timezone.now()
        active_quizzes = Quiz.objects.filter(
            Q(due_date__gte=now) | Q(due_date__isnull=True)
        ).select_related('course')
        
        if quiz_id:
            active_quizzes = active_quizzes.filter(id=quiz_id)
            if not active_quizzes.exists():
                return {'error': f'Quiz with ID {quiz_id} not found or expired'}
        
        results = {
            'total_quizzes': active_quizzes.count(),
            'total_students_notified': 0,
            'quizzes_processed': 0,
            'emails_sent': 0,
            'dashboard_alerts_created': 0,
            'reminders_created': 0,
            'errors': [],
            'details': []
        }
        
        for quiz in active_quizzes:
            try:
                quiz_result = self.process_quiz_reminders(quiz, reminder_type, dry_run)
                results['quizzes_processed'] += 1
                results['total_students_notified'] += quiz_result['students_notified']
                results['emails_sent'] += quiz_result['emails_sent']
                results['dashboard_alerts_created'] += quiz_result['alerts_created']
                results['reminders_created'] += quiz_result['reminders_created']
                results['details'].append(quiz_result)
                
            except Exception as e:
                error_msg = f"Error processing quiz {quiz.id}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        return results
    
    def process_quiz_reminders(self, quiz, reminder_type, dry_run=False):
        """Process reminders for a specific quiz - FIXED VERSION"""
        
        try:
            # Get students enrolled in the course
            enrolled_students = BaseUser.objects.filter(
                user_type='student',
                studentcourse__course=quiz.course,
                studentcourse__student__isnull=False
            ).distinct()
            
            students_notified = 0
            emails_sent = 0
            alerts_created = 0
            reminders_created = 0
            
            quiz_result = {
                'quiz_id': quiz.id,
                'quiz_title': quiz.title,
                'course_name': quiz.course.course_name,
                'students_notified': 0,
                'emails_sent': 0,
                'alerts_created': 0,
                'reminders_created': 0,
                'student_details': []
            }
            
            for student in enrolled_students:
                try:
                    # Additional safety check
                    if not student or not student.id:
                        continue
                        
                    # Check if student should receive reminder
                    should_notify = self.should_send_reminder_to_student(student, quiz, reminder_type)
                    
                    if should_notify:
                        # Get student's course progress with error handling
                        try:
                            student_course = StudentCourse.objects.get(
                                student=student,
                                course=quiz.course
                            )
                            course_progress = student_course.course_progress
                        except StudentCourse.DoesNotExist:
                            course_progress = 0
                            logger.warning(f"Student {student.id} not enrolled in course {quiz.course.id}")
                            continue
                        
                        if not dry_run:
                            # Send AI-powered email reminder
                            email_sent = send_ai_quiz_reminder(
                                student=student,
                                quiz=quiz,
                                course_progress=course_progress,
                                custom_message=f"Don't forget to attempt '{quiz.title}' for '{quiz.course.course_name}'"
                            )
                            
                            if email_sent:
                                emails_sent += 1
                            
                            # Create dashboard alert
                            alert_created = self.create_quiz_dashboard_alert(student, quiz)
                            if alert_created:
                                alerts_created += 1
                            
                            # Create individual quiz reminder record for each student
                            try:
                                QuizReminder.objects.create(
                                    quiz=quiz,
                                    student=student,  # FIXED: Add the required student field
                                    reminder_type=reminder_type
                                )
                                reminders_created += 1
                            except Exception as e:
                                logger.error(f"Error creating quiz reminder for student {student.id}: {str(e)}")
                        
                        students_notified += 1
                        
                        quiz_result['student_details'].append({
                            'student_id': student.id,
                            'student_name': student.get_full_name() or student.username,
                            'email': student.email,
                            'course_progress': course_progress,
                            'email_sent': not dry_run and email_sent,
                            'alert_created': not dry_run and alert_created,
                            'reminder_created': not dry_run
                        })
                        
                except Exception as e:
                    error_msg = f"Error processing student {getattr(student, 'id', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    quiz_result['student_details'].append({
                        'student_id': getattr(student, 'id', None),
                        'error': error_msg
                    })
        
            quiz_result.update({
                'students_notified': students_notified,
                'emails_sent': emails_sent,
                'alerts_created': alerts_created,
                'reminders_created': reminders_created
            })
            
            return quiz_result
            
        except Exception as e:
            logger.error(f"Error processing quiz {quiz.id}: {str(e)}")
            raise e

    def should_send_reminder_to_student(self, student, quiz, reminder_type):
        """Determine if a student should receive a quiz reminder"""
        
        # Check if student has notification preferences enabled
        try:
            pref = student.notification_preferences
            if not pref.email_notifications:
                return False
        except:
            # If no preferences exist, assume notifications are enabled
            pass
        
        # Check quiz attempt status based on reminder type
        has_attempted = QuizAttempt.objects.filter(
            student=student,
            quiz=quiz,
            is_completed=True
        ).exists()
        
        if reminder_type == 'pending':
            return not has_attempted
        elif reminder_type == 'all':
            return True
        elif reminder_type == 'custom':
            # For custom, you could add additional logic here
            return not has_attempted
        else:
            return not has_attempted

    def create_quiz_dashboard_alert(self, student, quiz):
        """Create dashboard alert for quiz reminder - FIXED VERSION"""
        try:
            # Check if alert already exists
            existing_alert = DashboardAlert.objects.filter(
                student=student,
                course=quiz.course,
                alert_type='quiz_pending',
                is_active=True
            ).exists()
            
            if not existing_alert:
                days_remaining = (quiz.due_date - timezone.now()).days if quiz.due_date else None
                
                if days_remaining and days_remaining <= 2:
                    message = f"🚨 URGENT: '{quiz.title}' due in {days_remaining} day(s)! Attempt now!"
                elif days_remaining and days_remaining <= 7:
                    message = f"📝 Reminder: '{quiz.title}' due in {days_remaining} days"
                else:
                    message = f"📚 New quiz available: '{quiz.title}'"
                
                DashboardAlert.objects.create(
                    student=student,
                    course=quiz.course,
                    alert_type='quiz_pending',
                    message=message,
                    is_active=True
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Error creating dashboard alert: {str(e)}")
            return False

    def print_results(self, results, dry_run=False):
        """Print formatted results to console"""
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No emails actually sent"))
        
        if 'error' in results:
            self.stdout.write(self.style.ERROR(f"❌ {results['error']}"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"✅ Quiz Reminder System Completed!"))
        self.stdout.write(f"📊 Summary:")
        self.stdout.write(f"   • Total Quizzes Processed: {results['quizzes_processed']}")
        self.stdout.write(f"   • Students Notified: {results['total_students_notified']}")
        self.stdout.write(f"   • Emails Sent: {results['emails_sent']}")
        self.stdout.write(f"   • Dashboard Alerts Created: {results['dashboard_alerts_created']}")
        self.stdout.write(f"   • Quiz Reminder Records: {results['reminders_created']}")
        
        if results['errors']:
            self.stdout.write(self.style.ERROR(f"❌ Errors: {len(results['errors'])}"))
            for error in results['errors'][:5]:  # Show first 5 errors
                self.stdout.write(f"   - {error}")
        
        # Show details for each quiz
        for detail in results['details']:
            self.stdout.write(f"\n📝 Quiz: {detail['quiz_title']}")
            self.stdout.write(f"   Course: {detail['course_name']}")
            self.stdout.write(f"   Students: {detail['students_notified']}")
            self.stdout.write(f"   Emails: {detail['emails_sent']}")
            self.stdout.write(f"   Alerts: {detail['alerts_created']}")
            self.stdout.write(f"   Reminders: {detail['reminders_created']}")