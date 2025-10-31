# ui/utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from ui.models import EmailLog
import traceback
from datetime import datetime

def get_time_based_greeting(time_period=None):
    """Get AI-optimized greeting based on time period or current time"""
    if time_period:
        # Use the scheduled time period
        greetings = {
            'morning': '🌅 Good Morning',
            'afternoon': '☀️ Good Afternoon', 
            'evening': '🌙 Good Evening',
            'demo': '👋 Hello'
        }
        return greetings.get(time_period, '👋 Hello')
    else:
        # Fallback to current time
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            return "🌅 Good Morning"
        elif 12 <= current_hour < 17:
            return "☀️ Good Afternoon"
        else:
            return "🌙 Good Evening"

def get_ai_progress_insight(progress, course_name, time_period=None):
    """AI-powered progress insights and recommendations with time context"""
    
    # Time-based context
    time_context = {
        'morning': {
            'start': "Perfect morning to continue",
            'motivation': "Start your day with productive learning!",
            'action': "Begin your day strong"
        },
        'afternoon': {
            'start': "Great afternoon for learning",
            'motivation': "Afternoon sessions boost retention!",
            'action': "Take a productive break"
        },
        'evening': {
            'start': "Ideal evening for progress",
            'motivation': "Evening learning enhances memory!",
            'action': "Wind down with learning"
        }
    }
    
    time_info = time_context.get(time_period, {
        'start': "Great time to continue",
        'motivation': "Keep up the momentum!",
        'action': "Continue your journey"
    })
    
    if progress < 25:
        return {
            'message': f"{time_info['start']} '{course_name}'! Building strong foundations is key to mastery.",
            'suggestion': f"{time_info['action']} by focusing on core concepts.",
            'emoji': "🚀",
            'time_context': time_info['motivation']
        }
    elif progress < 50:
        return {
            'message': f"{time_info['start']} '{course_name}'! You're building great momentum.",
            'suggestion': f"{time_info['action']} by connecting new concepts with previous learning.",
            'emoji': "💪",
            'time_context': time_info['motivation']
        }
    elif progress < 75:
        return {
            'message': f"{time_info['start']} '{course_name}'! This is where skills really develop.",
            'suggestion': f"{time_info['action']} with practical exercises.",
            'emoji': "🎯",
            'time_context': time_info['motivation']
        }
    else:
        return {
            'message': f"{time_info['start']} '{course_name}'! You're in the final stretch.",
            'suggestion': f"{time_info['action']} by reviewing key concepts.",
            'emoji': "🏆",
            'time_context': time_info['motivation']
        }

def get_time_specific_ai_message(student_name, course_name, progress, time_period):
    """Get AI message specific to the time period"""
    
    time_messages = {
        'morning': [
            f"Good morning {student_name}! 🌅 Perfect time to start your day with '{course_name}'.",
            f"Rise and shine {student_name}! ☀️ Morning learning sets a productive tone for your day.",
            f"Good morning {student_name}! 🎯 Start strong with '{course_name}' today."
        ],
        'afternoon': [
            f"Good afternoon {student_name}! 👋 Great time for a learning break with '{course_name}'.",
            f"Hi {student_name}! 💪 Afternoon sessions in '{course_name}' can boost your productivity.",
            f"Good afternoon {student_name}! 📚 Perfect time to continue your progress."
        ],
        'evening': [
            f"Good evening {student_name}! 🌙 Wind down with productive learning in '{course_name}'.",
            f"Hello {student_name}! 🌜 Evening is peaceful for focusing on '{course_name}'.",
            f"Good evening {student_name}! 🎯 End your day by advancing in '{course_name}'."
        ]
    }
    
    # Get base messages for the time period
    messages = time_messages.get(time_period, [f"Hello {student_name}! Continue learning in '{course_name}'."])
    
    # Add progress-specific messages
    progress_messages = []
    if progress >= 75:
        progress_messages.extend([
            f"You're doing amazing! 🚀 {progress}% complete - almost there!",
            f"Fantastic progress! ⭐ Just {100-progress}% left to finish!",
            f"Outstanding work! 🏆 You've mastered most of the content!"
        ])
    elif progress >= 50:
        progress_messages.extend([
            f"Great momentum! 📈 You're halfway through - keep going!",
            f"Excellent progress! 💪 You've covered the majority of the material!",
            f"Strong work! 🎯 You're building solid understanding!"
        ])
    elif progress >= 25:
        progress_messages.extend([
            f"Good start! 👣 You're building a strong foundation!",
            f"Nice progress! 📚 You're getting into the core concepts!",
            f"Building momentum! ⚡ You're establishing good learning habits!"
        ])
    else:
        progress_messages.extend([
            f"Every journey begins with a step! 🌱 You've started strong!",
            f"Beginning strong! 🚀 You're laying the groundwork for success!",
            f"Starting well! 💫 You're on the path to mastery!"
        ])
    
    import random
    time_message = random.choice(messages)
    progress_message = random.choice(progress_messages)
    
    return f"{time_message} {progress_message}"

def send_course_reminder_email(student, student_course, time_period=None, ai_message=None, ai_recommendation=None, pending_quizzes=None, high_completion_courses=None):
    """Enhanced AI-powered course reminder email with proper time context"""
    try:
        # Get base context
        context = student_course.get_reminder_context()
        context['course_url'] = f"{settings.SITE_URL}/courses/{student_course.course.id}/"
        
        # AI Enhancements
        progress = student_course.course_progress
        course_name = student_course.course.course_name
        student_name = student.first_name or student.username
        
        # Get time-specific greeting and AI insights
        time_greeting = get_time_based_greeting(time_period)
        ai_insight = get_ai_progress_insight(progress, course_name, time_period)
        
        # Use AI message if provided, otherwise generate time-specific one
        if not ai_message:
            ai_message = get_time_specific_ai_message(student_name, course_name, progress, time_period)
        
        if not ai_recommendation:
            ai_recommendation = ai_insight['suggestion']
        
        # Enhanced context with AI data and time context
        context.update({
            'ai_message': ai_message,
            'ai_recommendation': ai_recommendation,
            'time_greeting': time_greeting,
            'time_period': time_period or 'general',
            'pending_quizzes': pending_quizzes or [],
            'high_completion_courses': high_completion_courses or [],
            'has_quizzes': bool(pending_quizzes),
            'has_high_completion': bool(high_completion_courses),
            'time_context': ai_insight['time_context'],
        })
        
        subject = f"{time_greeting} - Continue {course_name}"
        
        # Render enhanced HTML template
        html_content = render_to_string('ai_course_reminder_email.html', context)
        text_content = strip_tags(html_content)
        
        # DEBUG: Print enhanced email details with time context
        print(f"🤖 AI Email preparing for: {student.email}")
        print(f"🕒 Time Period: {time_period or 'current time'}")
        print(f"📊 Progress: {progress}%")
        print(f"💡 AI Suggestion: {ai_recommendation}")
        print(f"🎯 Time Context: {ai_insight['time_context']}")
        
        # Create and send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send()
        
        # Enhanced logging with time and AI metrics
        EmailLog.objects.create(
            student=student,
            subject=subject,
            body=text_content,
            email_type='ai_course_reminder',
            success=True,
        )
        
        print(f"✅ AI-enhanced email sent successfully to: {student.email}")
        print(f"   🕒 Time: {time_greeting}")
        print(f"   📝 Message: {ai_message[:50]}...")
        return True
        
    except Exception as e:
        error_msg = f"AI Email Error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(f"❌ AI-enhanced email failed to {student.email}: {error_msg}")
        
        EmailLog.objects.create(
            student=student,
            subject=f"FAILED: AI Course Reminder",
            body=error_msg,
            email_type='ai_course_reminder',
            success=False
        )
        return False

def send_quiz_reminder_email(student, student_course, quiz=None, time_period=None):
    """Enhanced quiz reminder with AI context and proper time greeting"""
    try:
        context = student_course.get_reminder_context()
        course = student_course.course
        
        # If specific quiz provided, use its details
        if quiz:
            quiz_title = quiz.title
            quiz_url = f"{settings.SITE_URL}/courses/{course.id}/quiz/{quiz.id}/"
        else:
            quiz_title = f"{course.course_name} Quiz"
            quiz_url = f"{settings.SITE_URL}/courses/{course.id}/quiz/"
        
        # Get time-specific greeting
        time_greeting = get_time_based_greeting(time_period)
        
        context.update({
            'quiz_title': quiz_title,
            'quiz_url': quiz_url,
            'course_progress': student_course.course_progress,
            'time_greeting': time_greeting,
            'time_period': time_period or 'general',
        })
        
        # AI-powered quiz motivation based on progress and time
        progress = student_course.course_progress
        
        time_quiz_motivations = {
            'morning': {
                'low': "Perfect morning to test your foundational knowledge!",
                'medium': "Great morning opportunity to reinforce learning!",
                'high': "Morning quiz to validate your comprehensive understanding!"
            },
            'afternoon': {
                'low': "Ideal afternoon to assess your knowledge!",
                'medium': "Afternoon quiz to strengthen your skills!",
                'high': "Perfect time to demonstrate your mastery!"
            },
            'evening': {
                'low': "Evening quiz to consolidate your learning!",
                'medium': "Great evening to challenge your understanding!",
                'high': "Final evening step to confirm your expertise!"
            }
        }
        
        # Determine progress level
        if progress < 30:
            progress_level = 'low'
        elif progress < 70:
            progress_level = 'medium'
        else:
            progress_level = 'high'
        
        # Get time-specific motivation
        time_motivations = time_quiz_motivations.get(time_period, {
            'low': "Perfect time to test your knowledge!",
            'medium': "Great opportunity to reinforce learning!",
            'high': "Ideal moment to validate understanding!"
        })
        
        quiz_motivation = time_motivations.get(progress_level, "Great time to take your quiz!")
        
        context['quiz_motivation'] = quiz_motivation
        
        subject = f"📝 {time_greeting} - Quiz Reminder: {quiz_title}"
        
        # Use enhanced quiz template
        html_content = render_to_string('ai_quiz_reminder_email.html', context)
        text_content = strip_tags(html_content)
        
        # DEBUG: Print quiz reminder details with time context
        print(f"📝 AI Quiz reminder for: {student.email}")
        print(f"🕒 Time Period: {time_period or 'current time'}")
        print(f"🎯 Quiz: {quiz_title}")
        print(f"📊 Course Progress: {progress}%")
        print(f"💡 Motivation: {quiz_motivation}")
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send()
        
        # Enhanced logging
        EmailLog.objects.create(
            student=student,
            subject=subject,
            body=text_content,
            email_type='ai_quiz_reminder',
            success=True,
        )
        
        print(f"✅ AI quiz reminder sent to {student.email}")
        print(f"   🕒 Time: {time_greeting}")
        return True
        
    except Exception as e:
        error_msg = f"Quiz Reminder Error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(f"❌ AI quiz reminder failed to {student.email}: {error_msg}")
        
        EmailLog.objects.create(
            student=student,
            subject=f"FAILED: AI Quiz Reminder",
            body=error_msg,
            email_type='ai_quiz_reminder',
            success=False
        )
        return False

def send_high_completion_alert_email(student, student_course, time_period=None):
    """Special email for high-completion course alerts with time context"""
    try:
        progress = student_course.course_progress
        course_name = student_course.course.course_name
        remaining = 100 - progress
        
        # Get time-specific greeting
        time_greeting = get_time_based_greeting(time_period)
        
        context = {
            'student_name': student.first_name or student.username,
            'course_name': course_name,
            'progress': progress,
            'remaining': remaining,
            'course_url': f"{settings.SITE_URL}/courses/{student_course.course.id}/",
            'time_greeting': time_greeting,
            'time_period': time_period or 'general',
        }
        
        # AI-powered celebration messages with time context
        time_celebrations = {
            'morning': [
                f"🎉 Amazing morning progress! You're {progress}% through {course_name}!",
                f"🚀 Fantastic morning achievement! Only {remaining}% left!",
                f"🏆 Outstanding morning work! {progress}% complete!"
            ],
            'afternoon': [
                f"🎉 Great afternoon progress! You're {progress}% through {course_name}!",
                f"🚀 Excellent afternoon achievement! Only {remaining}% left!",
                f"🏆 Superb afternoon work! {progress}% complete!"
            ],
            'evening': [
                f"🎉 Wonderful evening progress! You're {progress}% through {course_name}!",
                f"🚀 Impressive evening achievement! Only {remaining}% left!",
                f"🏆 Brilliant evening work! {progress}% complete!"
            ]
        }
        
        celebrations = time_celebrations.get(time_period, [
            f"🎉 Amazing! You're {progress}% through {course_name}!",
            f"🚀 Fantastic progress! Only {remaining}% left!",
            f"🏆 Outstanding! {progress}% complete!"
        ])
        
        import random
        context['celebration_message'] = random.choice(celebrations)
        
        subject = f"🎯 {context['celebration_message']}"
        
        html_content = render_to_string('high_completion_alert_email.html', context)
        text_content = strip_tags(html_content)
        
        print(f"🏆 High-completion alert for: {student.email}")
        print(f"🕒 Time Period: {time_period or 'current time'}")
        print(f"📊 Progress: {progress}% complete")
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        email.send()
        
        EmailLog.objects.create(
            student=student,
            subject=subject,
            body=text_content,
            email_type='high_completion_alert',
            success=True,
        )
        
        print(f"✅ High-completion alert sent to {student.email}")
        print(f"   🕒 Time: {time_greeting}")
        return True
        
    except Exception as e:
        error_msg = f"High Completion Alert Error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(f"❌ High-completion alert failed: {error_msg}")
        
        EmailLog.objects.create(
            student=student,
            subject="FAILED: High Completion Alert",
            body=error_msg,
            email_type='high_completion_alert',
            success=False
        )
        return False

# Maintain backward compatibility
def send_legacy_course_reminder_email(student, student_course):
    """Legacy function for backward compatibility"""
    return send_course_reminder_email(student, student_course)

def send_legacy_quiz_reminder_email(student, student_course):
    """Legacy function for backward compatibility"""
    return send_quiz_reminder_email(student, student_course)