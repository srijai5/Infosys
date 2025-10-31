# ui/context_processors.py
from django.utils import timezone
from .models import StudentCourse, Video, StudentVideoProgress

def high_completion_alerts(request):
    """Add high completion alerts to template context"""
    context = {
        'high_completion_alerts': [],
        'high_completion_courses': [],
        'has_high_completion_alerts': False,
    }
    
    if request.user.is_authenticated and hasattr(request.user, 'is_student') and request.user.is_student:
        try:
            # Get all student courses that are not completed
            student_courses = StudentCourse.objects.filter(
                student=request.user,
                completed=False
            ).select_related('course')
            
            # Filter courses with high completion (75%+)
            high_completion_courses = []
            high_completion_alerts_list = []
            
            for student_course in student_courses:
                # Calculate progress
                total_videos = Video.objects.filter(course=student_course.course).count()
                watched_videos = StudentVideoProgress.objects.filter(
                    student_course=student_course, 
                    watched=True
                ).count()
                progress = (watched_videos / total_videos * 100) if total_videos > 0 else 0
                
                # Check if course qualifies for high completion alert
                if 75 <= progress < 100:
                    # Add to high completion courses list
                    high_completion_courses.append({
                        'student_course': student_course,
                        'course': student_course.course,
                        'progress': progress,
                        'watched_videos': watched_videos,
                        'total_videos': total_videos,
                    })
                    
                    # Create alert data
                    if progress >= 95:
                        alert_type = 'completion_urgent'
                        priority = 'urgent'
                        icon = '🔥'
                        title = 'Almost Complete!'
                    elif progress >= 90:
                        alert_type = 'almost_complete' 
                        priority = 'high'
                        icon = '⚡'
                        title = 'Great Progress!'
                    else:
                        alert_type = 'high_completion'
                        priority = 'medium'
                        icon = '🎯'
                        title = 'Well Done!'
                    
                    # Generate message based on progress
                    if progress >= 95:
                        message = f"You're at {progress:.1f}% completion! Just finish these last few videos to complete '{student_course.course.course_name}'! 🎉"
                    elif progress >= 90:
                        message = f"Amazing! You're at {progress:.1f}% completion for '{student_course.course.course_name}'. Almost there! 🔥"
                    else:
                        message = f"Great progress! You've completed {progress:.1f}% of '{student_course.course.course_name}'. Keep going! ⚡"
                    
                    high_completion_alerts_list.append({
                        'id': student_course.id,
                        'student_course': student_course,
                        'course': student_course.course,
                        'alert_type': alert_type,
                        'priority': priority,
                        'message': message,
                        'progress': progress,
                        'icon': icon,
                        'title': title,
                        'watched_videos': watched_videos,
                        'total_videos': total_videos,
                    })
            
            context.update({
                'high_completion_alerts': high_completion_alerts_list,
                'high_completion_courses': high_completion_courses,
                'has_high_completion_alerts': len(high_completion_alerts_list) > 0,
            })
            
        except Exception as e:
            print(f"Error in high_completion_alerts context processor: {e}")
    
    return context