from django.utils import timezone
from datetime import datetime
from django.db.models import Q
from ui.models import BaseUser, DashboardAlert, StudentCourse, CourseContent, NotificationPreference, Quiz, QuizAttempt
from ui.utils import send_course_reminder_email, send_quiz_reminder_email
import logging
import smtplib
from email.mime.text import MIMEText  # CORRECTED: MIMEText not MimeText
from email.mime.multipart import MIMEMultipart  # CORRECTED: MIMEMultipart not MimeMultipart
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class AINotificationService:
    
    @staticmethod
    def get_ai_personalized_message(student, student_course, time_period):
        """AI-powered personalized messaging based on progress and behavior"""
        course = student_course.course
        progress = student_course.course_progress
        student_name = student.first_name or student.username
        
        # AI Progress Analysis
        progress_category = AINotificationService.analyze_progress_trend(student_course)
        learning_style = AINotificationService.analyze_learning_pattern(student, student_course)
        
        # Time-based templates with AI personalization
        time_templates = {
            'morning': {
                'low': f"Good morning {student_name}! 🌅 Perfect time to start '{course.course_name}'. Based on your learning pattern, we recommend starting with short, focused sessions.",
                'medium': f"Good morning {student_name}! 🌞 You're making great progress in '{course.course_name}'. Your consistency is paying off - today you could reach the next milestone!",
                'high': f"Good morning {student_name}! 🚀 You're at {progress}% completion! Today could be your finish line in '{course.course_name}'!",
                'stalled': f"Good morning {student_name}! 💪 Let's reignite your progress in '{course.course_name}'. Sometimes a fresh start in the morning is all we need!"
            },
            'afternoon': {
                'low': f"Hi {student_name}! 👋 Afternoon learning break? Perfect time to make progress in '{course.course_name}'.",
                'medium': f"Hi {student_name}! 💪 Great time for a learning session in '{course.course_name}'. Your steady progress shows great dedication!",
                'high': f"Hi {student_name}! 🎯 So close to finishing '{course.course_name}'! A quick afternoon session could get you across the finish line.",
                'stalled': f"Hi {student_name}! 🔄 Noticed you haven't progressed recently. The afternoon is a great time to get back on track with '{course.course_name}'."
            },
            'evening': {
                'low': f"Good evening {student_name}! 🌙 Wind down with some learning in '{course.course_name}'. Evening sessions can be very productive!",
                'medium': f"Good evening {student_name}! 🌜 Perfect time to continue '{course.course_name}'. You're building valuable skills every day.",
                'high': f"Good evening {student_name}! 🌟 Only {100-progress}% left to complete '{course.course_name}'! One final push this evening!",
                'stalled': f"Good evening {student_name}! 📚 Evening is a great time to revisit '{course.course_name}'. Let's complete one small module tonight!"
            }
        }
        
        return time_templates[time_period][progress_category]
    
    @staticmethod
    def analyze_progress_trend(student_course):
        """AI: Analyze progress trend and categorize"""
        progress = student_course.course_progress
        
        # Simple AI logic - you can enhance this with ML
        if progress < 25:
            return 'low'
        elif progress < 75:
            return 'medium'
        elif progress < 100:
            return 'high'
        else:
            return 'completed'
    
    @staticmethod
    def analyze_learning_pattern(student, student_course):
        """AI: Analyze student's learning patterns"""
        # This can be enhanced with actual learning analytics
        # For now, returning a basic pattern
        return 'consistent'  # Could be 'consistent', 'burst', 'stalled', etc.
    
    @staticmethod
    def get_ai_recommended_content(student, student_course):
        """AI: Recommend specific content based on progress and behavior"""
        progress = student_course.course_progress
        
        # Simple recommendation logic - enhance with actual AI
        if progress < 30:
            return "Start with the foundational concepts and basic exercises."
        elif progress < 60:
            return "Focus on practical applications and intermediate topics."
        elif progress < 90:
            return "Tackle advanced concepts and real-world projects."
        else:
            return "Review key concepts and prepare for final assessment."

class NotificationService:
    
    @staticmethod
    def get_current_reminder_period():
        """Determine current reminder time period"""
        now = timezone.now()
        current_hour = now.hour
        
        # Define reminder periods
        if 8 <= current_hour <= 10:  # 8 AM - 10 AM
            return 'morning'
        elif 13 <= current_hour <= 15:  # 1 PM - 3 PM
            return 'afternoon'
        elif 18 <= current_hour <= 20:  # 6 PM - 8 PM
            return 'evening'
        else:
            return None
    
    @staticmethod
    def should_send_reminder(student):
        """Check if we should send reminder based on frequency and time"""
        current_period = NotificationService.get_current_reminder_period()
        
        if not current_period:
            return False
            
        try:
            pref = student.notification_preferences
            if pref.reminder_frequency == 'multiple':
                return True
            elif pref.reminder_frequency == 'daily' and current_period == 'morning':
                return True
            elif pref.reminder_frequency == 'disabled':
                return False
        except NotificationPreference.DoesNotExist:
            # Create default preferences if they don't exist
            NotificationPreference.objects.create(student=student)
            return True
            
        return False
    
    @staticmethod
    def get_pending_quizzes(student):
        """TASK 2: Get all pending quizzes for a student"""
        try:
            # Get courses the student is enrolled in
            enrolled_courses = StudentCourse.objects.filter(
                student=student,
                status='in_progress'
            ).values_list('course_id', flat=True)
            
            # Find quizzes they haven't attempted
            pending_quizzes = Quiz.objects.filter(
                course_id__in=enrolled_courses
            ).exclude(
                quizattempt__student=student
            ).select_related('course')
            
            return list(pending_quizzes)
        except Exception as e:
            logger.error(f"Error getting pending quizzes for {student.username}: {str(e)}")
            return []
    
    @staticmethod
    def check_high_completion_courses(student):
        """TASK 3: Check for courses with high completion percentage"""
        try:
            high_completion_courses = StudentCourse.objects.filter(
                student=student,
                course_progress__gte=75,
                course_progress__lt=100,
                status='in_progress'
            ).select_related('course')
            
            return list(high_completion_courses)
        except Exception as e:
            logger.error(f"Error checking high completion courses for {student.username}: {str(e)}")
            return []
    
    @staticmethod
    def send_intelligent_daily_reminders():
        """Enhanced daily reminders with AI personalization and all milestone features"""
        students = BaseUser.objects.filter(
            user_type='student',
            is_active=True
        )
        
        current_period = NotificationService.get_current_reminder_period()
        if not current_period:
            logger.info("Not in scheduled reminder period")
            return {'status': 'skipped', 'reason': 'outside_reminder_hours'}
        
        results = {
            'total_students': students.count(),
            'emails_sent': 0,
            'quiz_reminders': 0,
            'high_completion_alerts': 0,
            'ai_personalized': 0,
            'errors': []
        }
        
        for student in students:
            try:
                # Check if we should send reminders now
                if not NotificationService.should_send_reminder(student):
                    continue
                
                # Get student's active courses
                student_courses = StudentCourse.objects.filter(
                    student=student,
                    status='in_progress',
                    completed=False
                ).select_related('course')
                
                if not student_courses.exists():
                    continue
                
                # TASK 2: Check for pending quizzes
                pending_quizzes = NotificationService.get_pending_quizzes(student)
                
                # TASK 3: Check for high completion courses
                high_completion_courses = NotificationService.check_high_completion_courses(student)
                
                # Process each active course
                for student_course in student_courses:
                    try:
                        pref = student.notification_preferences
                        if pref.email_notifications:
                            # AI-Personalized Message
                            ai_message = AINotificationService.get_ai_personalized_message(
                                student, student_course, current_period
                            )
                            
                            # AI Content Recommendation
                            ai_recommendation = AINotificationService.get_ai_recommended_content(
                                student, student_course
                            )
                            
                            # Send enhanced email
                            success = send_course_reminder_email(
                                student, 
                                student_course,
                                ai_message,
                                ai_recommendation,
                                pending_quizzes,
                                high_completion_courses
                            )
                            
                            if success:
                                results['emails_sent'] += 1
                                results['ai_personalized'] += 1
                                logger.info(f"AI-enhanced reminder sent to {student.email}")
                    
                    except Exception as e:
                        logger.error(f"Error sending course reminder to {student.email}: {str(e)}")
                
                # Send dedicated quiz reminders if any
                if pending_quizzes and student.notification_preferences.email_notifications:
                    for quiz in pending_quizzes:
                        try:
                            quiz_course = StudentCourse.objects.get(
                                student=student, 
                                course=quiz.course
                            )
                            success = send_quiz_reminder_email(student, quiz_course, quiz)
                            if success:
                                results['quiz_reminders'] += 1
                                logger.info(f"Quiz reminder sent to {student.email} for {quiz.title}")
                        except Exception as e:
                            logger.error(f"Error sending quiz reminder: {str(e)}")
                
                # Create dashboard alerts for high completion courses
                for high_course in high_completion_courses:
                    try:
                        pref = student.notification_preferences
                        if pref.dashboard_alerts:
                            alert_created = NotificationService.create_high_completion_alert(student, high_course)
                            if alert_created:
                                results['high_completion_alerts'] += 1
                    except Exception as e:
                        logger.error(f"Error creating alert for {student.username}: {str(e)}")
                    
            except Exception as e:
                error_msg = f"Error processing {student.username}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        logger.info(f"AI Notification service completed: {results}")
        return results
    
    @staticmethod
    def create_high_completion_alert(student, student_course):
        """Create dashboard alert for high completion course"""
        try:
            progress = student_course.course_progress
            remaining = 100 - progress
            
            # AI-powered motivational messages
            motivational_messages = [
                f"You're {progress}% complete with {student_course.course.course_name}! Almost there! 🎯",
                f"Great work! Only {remaining}% left in {student_course.course.course_name}. You've got this! 💪",
                f"🎉 {progress}% completed! Finish strong with {student_course.course.course_name}",
                f"You're in the final stretch! {remaining}% to go in {student_course.course.course_name} 🚀"
            ]
            
            import random
            message = random.choice(motivational_messages)
            
            # Check if alert already exists
            existing_alert = DashboardAlert.objects.filter(
                student=student,
                course=student_course.course,
                alert_type='high_completion',
                is_active=True
            ).exists()
            
            if not existing_alert:
                DashboardAlert.objects.create(
                    student=student,
                    course=student_course.course,
                    alert_type='high_completion',
                    message=message,
                    priority='high' if progress >= 90 else 'medium',
                    is_active=True
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Error creating high completion alert: {str(e)}")
            return False
    
    @staticmethod
    def get_student_alerts(student):
        """Get active alerts for student dashboard"""
        return DashboardAlert.objects.filter(
            student=student,
            is_active=True
        ).select_related('course').order_by('-priority', '-created_at')
    
    @staticmethod
    def dismiss_alert(alert_id, student):
        """Dismiss a dashboard alert"""
        try:
            alert = DashboardAlert.objects.get(id=alert_id, student=student)
            alert.is_active = False
            alert.dismissed_at = timezone.now()
            alert.save()
            return True
        except DashboardAlert.DoesNotExist:
            return False
    
    @staticmethod
    def send_immediate_quiz_notification(student, course):
        """Send immediate notification when quiz is added to course"""
        try:
            student_course = StudentCourse.objects.get(student=student, course=course)
            if student.notification_preferences.email_notifications:
                return send_quiz_reminder_email(student, student_course)
            return False
        except StudentCourse.DoesNotExist:
            logger.warning(f"Student {student.username} not enrolled in course {course.course_name}")
            return False

# Backward compatibility
def send_daily_reminders():
    """Legacy function - now uses AI-enhanced version"""
    return NotificationService.send_intelligent_daily_reminders()




def get_time_greeting():
    """Get appropriate greeting based on time of day"""
    hour = timezone.now().hour
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 21:
        return "Good evening"
    else:
        return "Hello"

def get_quiz_motivation(progress):
    """AI-inspired motivational messages based on progress"""
    if progress >= 80:
        return "You're acing this course! This quiz will help you master the final concepts."
    elif progress >= 60:
        return "Great progress! This quiz will reinforce your understanding and boost your confidence."
    elif progress >= 40:
        return "You're halfway there! This quiz will help solidify your learning so far."
    elif progress >= 20:
        return "Good start! This quiz will help you build momentum and identify key areas to focus on."
    else:
        return "Let's get started! This quiz will help you establish a strong foundation."

def send_ai_quiz_reminder(student, quiz, course_progress, custom_message=''):
    """Send AI-powered quiz reminder email"""
    try:
        # Prepare email content with AI-inspired personalization
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
            'quiz_url': f"/student/quiz/{quiz.id}/take/",  # Relative URL
            'custom_message': custom_message,
            'settings': {'SITE_URL': 'http://localhost:8000'}  # Add settings context
        }
        
        # Render email template
        email_html = render_to_string('ai_quiz_reminder_email.html', context)
        
        # Create email message - FIXED IMPORTS
        msg = MIMEMultipart('alternative')  # FIXED: MIMEMultipart not MimeMultipart
        msg['Subject'] = f"📝 Quiz Reminder: {quiz.title}"
        msg['From'] = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@studysite.com')
        msg['To'] = student.email
        
        # Create plain text version
        text = f"""
        {time_greeting} {student.first_name or student.username},
        
        {quiz_motivation}
        
        Quiz: {quiz.title}
        Course: {quiz.course.course_name}
        Due Date: {quiz.due_date.strftime("%B %d, %Y at %I:%M %p") if quiz.due_date else "No due date"}
        
        Your course progress: {course_progress}%
        
        Take the quiz here: http://localhost:8000/student/quiz/{quiz.id}/take/
        
        Best regards,
        StudyPortal Team
        """
        
        part1 = MIMEText(text, 'plain')  # FIXED: MIMEText not MimeText
        part2 = MIMEText(email_html, 'html')  # FIXED: MIMEText not MimeText
        
        msg.attach(part1)
        msg.attach(part2)
        
        # For development: print email details instead of sending
        print("=" * 50)
        print("📧 QUIZ REMINDER EMAIL (Development Mode)")
        print("=" * 50)
        print(f"To: {student.email}")
        print(f"Subject: {msg['Subject']}")
        print(f"Student: {student.get_full_name() or student.username}")
        print(f"Quiz: {quiz.title}")
        print(f"Course: {quiz.course.course_name}")
        print(f"Progress: {course_progress}%")
        print(f"Due Date: {quiz.due_date}")
        print("=" * 50)
        
        # In development, we'll just log the email instead of sending
        logger.info(f"Quiz reminder prepared for {student.email}: {quiz.title}")
        
        # TODO: Uncomment when ready to send actual emails
        # with smtplib.SMTP('localhost') as server:
        #     server.send_message(msg)
        
        return True
        
    except Exception as e:
        logger.error(f"Error sending quiz reminder email: {str(e)}")
        print(f"DEBUG - Email error: {str(e)}")  # Additional debug info
        return False