from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from .models import BaseUser, StudentCourse, Course
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.views.decorators.csrf import csrf_exempt
from .models import Course,Video
from .forms import CourseForm
from django.contrib.auth.decorators import user_passes_test
import json
from django.db.models import Avg
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers import serialize
from datetime import datetime
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from .services import send_ai_quiz_reminder, get_time_greeting, get_quiz_motivation
from django.db.models import Q, Count, Avg
from datetime import datetime, timedelta

from django.views.decorators.http import require_GET



from .models import (
    Activity,  BaseUser, 
    Course, CourseContent, StudentCourse, Video, StudentVideoProgress,Quiz, Question, Choice, QuizAttempt, QuizReminder,StudentAnswer
)
from .forms import CourseForm

# Add this right after your imports in views.py
# Add this right after your imports in views.py
def is_admin(user):
    return user.user_type == 'admin' if hasattr(user, 'user_type') else False



# ----------------------------
# Home
# ----------------------------
def home(request):
    return render(request, 'index.html')


# ----------------------------
# Student Authentication
# ----------------------------
def student_register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('student_register')

        if BaseUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('student_register')

        if BaseUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect('student_register')

        BaseUser.objects.create_user(
            username=username, 
            email=email, 
            password=password,
            first_name=first_name,
            last_name=last_name,
            user_type='student'
        )
        messages.success(request, "Account created successfully! Please login.")
        return redirect('student_login')

    return render(request, 'register.html')

def student_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user and user.user_type == 'student':
            login(request, user)
            return redirect('student_dashboard')
        messages.error(request, "Invalid credentials.")
    return render(request, 'login.html')


@login_required
def student_logout(request):
    logout(request)
    return redirect('student_login')


# ----------------------------
# Student Dashboard
# ----------------------------
# In views.py - Update student_dashboard function
# In views.py - Update student_dashboard function
@login_required
def student_dashboard(request):
    student = request.user

    enrolled_courses = StudentCourse.objects.filter(student=student).select_related('course').prefetch_related('video_progress', 'course__videos')

    courses_progress = []
    total_courses = enrolled_courses.count()
    completed_courses = 0
    in_progress_courses = 0

    for sc in enrolled_courses:
        total_videos = sc.course.videos.count()
        watched_videos = sc.video_progress.filter(watched=True).count()
        progress = (watched_videos / total_videos * 100) if total_videos > 0 else 0

        if sc.completed or progress == 100:
            completed_courses += 1
        else:
            in_progress_courses += 1

        courses_progress.append({
            'student_course': sc,
            'progress': progress,
        })

    # ========== ADD QUIZ DATA TO DASHBOARD ==========
    quiz_data = update_student_dashboard_with_quizzes(request)

    context = {
        'user': student,
        'courses_progress': courses_progress,
        'total_courses': total_courses,
        'completed_courses': completed_courses,
        'in_progress_courses': in_progress_courses,
        'pending_quizzes': quiz_data['pending_quizzes'],
        'recent_attempts': quiz_data['recent_attempts'],
        'total_pending_quizzes': quiz_data['total_pending_quizzes'],
        'completed_quizzes': quiz_data['completed_quizzes'],
        # Remove high_completion_courses from here - it will be handled by context processor
    }

    return render(request, 'student_dashboard.html', context)


# Add to views.py


def student_dashboard_data(request):
    student = request.user

    enrolled_courses = StudentCourse.objects.filter(student=student).select_related('course')
    courses_progress = []

    for sc in enrolled_courses:
        total_videos = sc.course.videos.count()
        watched_videos = sc.video_progress.filter(watched=True).count()
        progress = int((watched_videos / total_videos) * 100) if total_videos > 0 else 0
        courses_progress.append({
            'course_name': sc.course.course_name,
            'progress': progress,
            'completed': sc.completed
        })

    data = {
        'enrolled_courses': courses_progress,
        'total_courses': enrolled_courses.count(),
        'completed_courses': enrolled_courses.filter(completed=True).count(),
    }
    return JsonResponse(data)


# ----------------------------
# Courses
# ----------------------------
@login_required
def enroll_courses_list(request):
    courses = Course.objects.all()
    enrolled_course_ids = StudentCourse.objects.filter(student=request.user).values_list('course_id', flat=True)
    return render(request, 'enroll_courses.html', {'courses': courses, 'enrolled_course_ids': enrolled_course_ids})


@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not StudentCourse.objects.filter(student=request.user, course=course).exists():
        StudentCourse.objects.create(student=request.user, course=course)
    return redirect('enroll_courses')
# In your course detail view

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    videos = Video.objects.filter(course=course).order_by('order')
    student_course = get_object_or_404(StudentCourse, student=request.user, course=course)  
    
    # Get watched videos for this student and course
    watched_videos = []
    if student_course:
        watched_videos = StudentVideoProgress.objects.filter(
            student_course=student_course,
            watched=True
        ).values_list('video_id', flat=True)
    
    # Calculate progress percentage
    total_videos = videos.count()
    watched_videos_count = len(watched_videos)
    progress_percent = 0
    if total_videos > 0:
        progress_percent = int((watched_videos_count / total_videos) * 100)
    
    # Calculate remaining videos
    remaining_videos = total_videos - watched_videos_count
    
    # Get quizzes for this course
    quizzes = Quiz.objects.filter(course=course).order_by('due_date')
    
    # Get quiz attempts for this student
    quiz_attempts = {}
    for quiz in quizzes:
        attempt = QuizAttempt.objects.filter(student=request.user, quiz=quiz).first()
        quiz_attempts[quiz.id] = attempt
    
    context = {
        'course': course,
        'videos': videos,
        'student_course': student_course,
        'watched_videos': list(watched_videos),
        'watched_videos_count': watched_videos_count,
        'total_videos': total_videos,
        'progress_percent': progress_percent,
        'remaining_videos': remaining_videos,
        'quizzes': quizzes,  # Add quizzes to context
        'quiz_attempts': quiz_attempts, 
        'current_time': timezone.now(), # Add quiz attempts to context
    }
    
    return render(request, 'course_detail.html', context)

@login_required
def mark_video_watched(request, student_course_id, video_id):
    student_course = get_object_or_404(StudentCourse, id=student_course_id, student=request.user)
    video = get_object_or_404(Video, id=video_id, course=student_course.course)

    progress, created = StudentVideoProgress.objects.get_or_create(
        student_course=student_course, 
        video=video
    )

    if not progress.watched:
        progress.watched = True
        progress.watched_at = timezone.now()
        progress.save()

        # Update course progress
        total_videos = student_course.course.videos.count()
        watched_videos = student_course.video_progress.filter(watched=True).count()
        
        # Mark course as completed if all videos are watched
        if watched_videos >= total_videos and total_videos > 0:
            student_course.completed = True
            student_course.completed_at = timezone.now()
            student_course.status = 'completed'
        
        student_course.save()

    return JsonResponse({
        "success": True,
        "video_id": video.id,
        "watched": True,
        "total_videos": student_course.course.videos.count(),
        "watched_videos": student_course.video_progress.filter(watched=True).count(),
        "course_completed": student_course.completed
    })

@login_required
def my_courses(request):
    student_courses = StudentCourse.objects.filter(student=request.user).select_related('course').prefetch_related('video_progress', 'course__videos')

    courses_with_progress = []
    total_courses = student_courses.count()
    completed_courses_count = 0
    in_progress_courses_count = 0
    total_watched_videos_count = 0

    for sc in student_courses:
        total_videos = sc.course.videos.count()
        watched_videos = sc.video_progress.filter(watched=True).count()
        progress_percent = int((watched_videos / total_videos) * 100) if total_videos > 0 else 0
        
        # Use the SAME logic as dashboard
        completed = sc.completed or progress_percent == 100
        
        # Update database to match dashboard logic (if needed)
        if progress_percent == 100 and not sc.completed:
            sc.completed = True
            sc.completed_at = timezone.now()
            sc.save()
        
        # Update counters using the SAME logic as dashboard
        if completed:
            completed_courses_count += 1
        else:
            in_progress_courses_count += 1

        total_watched_videos_count += watched_videos

        courses_with_progress.append({
            'sc': sc,
            'total_videos': total_videos,
            'watched_videos': watched_videos,
            'progress_percent': progress_percent,
            'completed': completed
        })

    context = {
        'courses': courses_with_progress,
        'total_courses': total_courses,
        'completed_courses': completed_courses_count,
        'in_progress_courses': in_progress_courses_count,
        'total_watched_videos': total_watched_videos_count,
    }

    return render(request, 'my_courses.html', context)


@login_required
def complete_course(request, course_id):
    student_course = get_object_or_404(StudentCourse, student=request.user, id=course_id)
    student_course.completed = True
    student_course.completed_at = timezone.now()
    student_course.save()
    messages.success(request, f"Marked '{student_course.course.course_name}' as completed.")
    return redirect('my_courses')

# views.py

@login_required
@user_passes_test(is_admin)
def course_data(request, course_id):
    """Admin view to see detailed course information"""
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')
    
    course = get_object_or_404(Course, id=course_id)
    videos = Video.objects.filter(course=course).order_by('order')
    enrolled_students = StudentCourse.objects.filter(course=course).select_related('student')
    
    # Calculate enrollment statistics
    total_students = enrolled_students.count()
    completed_students = enrolled_students.filter(completed=True).count()
    
    # Calculate average progress
    total_progress = 0
    student_progress_data = []
    
    for enrollment in enrolled_students:
        progress, watched_videos, total_videos = calculate_course_progress(enrollment)
        total_progress += progress
        
        student_progress_data.append({
            'student': enrollment.student,
            'progress': progress,
            'watched_videos': watched_videos,
            'total_videos': total_videos,
            'completed': enrollment.completed,
            'enrolled_date': enrollment.enrolled_at
        })
    
    avg_progress = total_progress / total_students if total_students > 0 else 0
    
    context = {
        'course': course,
        'videos': videos,
        'enrolled_students': student_progress_data,
        'total_students': total_students,
        'completed_students': completed_students,
        'avg_progress': round(avg_progress, 1),
    }
    
    return render(request, 'course_data.html', context)

# ----------------------------
# Quiz Management
# ----------------------------

# ============================================================================
# Quiz Management - Missing Views
# ============================================================================

# ============================================================================
# Quiz Management - Professional Views
# ============================================================================

@login_required
@user_passes_test(is_admin)
def admin_view_quiz(request, quiz_id):
    """View quiz details"""
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')
    
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all().prefetch_related('choices')
    
    # Calculate statistics
    total_attempts = quiz.attempts.count()
    if total_attempts > 0:
        avg_score = quiz.attempts.aggregate(avg_score=Avg('score'))['avg_score'] or 0
        passing_attempts = quiz.attempts.filter(score__gte=quiz.passing_score).count()
        pass_rate = (passing_attempts / total_attempts) * 100
    else:
        avg_score = 0
        pass_rate = 0
    
    # Get enrolled students count
    enrolled_students = StudentCourse.objects.filter(course=quiz.course).count()
    pending_students = enrolled_students - total_attempts
    
    context = {
        'quiz': quiz,
        'questions': questions,
        'total_attempts': total_attempts,
        'avg_score': round(avg_score, 1),
        'pass_rate': round(pass_rate, 1),
        'enrolled_students': enrolled_students,
        'pending_students': pending_students,
        'current_date': timezone.now().strftime('%B %d, %Y'),
        'current_time': timezone.now(),
    }
    
    return render(request, 'admin_view_quiz.html', context)

@login_required
@user_passes_test(is_admin)
def admin_edit_quiz(request, quiz_id):
    """Edit an existing quiz"""
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')
    
    quiz = get_object_or_404(Quiz, id=quiz_id)
    courses = Course.objects.all()
    
    # Add current date and time for the template header
    current_time = timezone.now()
    
    if request.method == 'POST':
        try:
            # Update quiz basic info
            course = get_object_or_404(Course, id=request.POST.get('course'))
            quiz.course = course
            quiz.title = request.POST.get('title')
            quiz.description = request.POST.get('description', '')
            quiz.due_date = request.POST.get('due_date')
            quiz.time_limit = int(request.POST.get('time_limit', 30))
            quiz.passing_score = int(request.POST.get('passing_score', 70))
            quiz.is_active = request.POST.get('is_active') == 'on'
            quiz.save()
            
            # Handle questions - delete existing and create new
            quiz.questions.all().delete()
            
            # Create new questions from form data
            question_count = 0
            for key, value in request.POST.items():
                if key.startswith('question_text_') and value.strip():
                    question_num = key.split('_')[-1]
                    question_text = value.strip()
                    option_a = request.POST.get(f'option_a_{question_num}', '').strip()
                    option_b = request.POST.get(f'option_b_{question_num}', '').strip()
                    option_c = request.POST.get(f'option_c_{question_num}', '').strip()
                    option_d = request.POST.get(f'option_d_{question_num}', '').strip()
                    correct_answer = request.POST.get(f'correct_answer_{question_num}')
                    
                    if question_text and option_a and option_b and correct_answer:
                        question = Question.objects.create(
                            quiz=quiz,
                            text=question_text,
                            order=question_count + 1
                        )
                        
                        # Create choices
                        Choice.objects.create(
                            question=question, 
                            choice_text=option_a, 
                            is_correct=(correct_answer == 'A')
                        )
                        Choice.objects.create(
                            question=question, 
                            choice_text=option_b, 
                            is_correct=(correct_answer == 'B')
                        )
                        if option_c:
                            Choice.objects.create(
                                question=question, 
                                choice_text=option_c, 
                                is_correct=(correct_answer == 'C')
                            )
                        if option_d:
                            Choice.objects.create(
                                question=question, 
                                choice_text=option_d, 
                                is_correct=(correct_answer == 'D')
                            )
                        
                        question_count += 1
            
            messages.success(request, f'✅ Quiz "{quiz.title}" updated successfully with {question_count} questions!')
            return redirect('admin_quizzes')
            
        except Exception as e:
            messages.error(request, f'❌ Error updating quiz: {str(e)}')
    
    # Prepare existing questions data for template
    questions_data = []
    for question in quiz.questions.all().prefetch_related('choices'):
        choices = list(question.choices.all().order_by('id'))
        correct_choice = None
        
        # Find correct answer
        for i, choice in enumerate(choices):
            if choice.is_correct:
                correct_choice = ['A', 'B', 'C', 'D'][i]
                break
        
        questions_data.append({
            'text': question.text,
            'option_a': choices[0].choice_text if len(choices) > 0 else '',
            'option_b': choices[1].choice_text if len(choices) > 1 else '',
            'option_c': choices[2].choice_text if len(choices) > 2 else '',
            'option_d': choices[3].choice_text if len(choices) > 3 else '',
            'correct_answer': correct_choice
        })
    
    context = {
        'quiz': quiz,
        'courses': courses,
        'questions_data': questions_data,
        'current_date': current_time.strftime('%B %d, %Y'),
        'current_time': current_time.strftime('%I:%M %p'),
        'action': 'Edit'
    }
    return render(request, 'admin_create_quiz.html', context)


@login_required
@user_passes_test(is_admin)
def admin_delete_quiz(request, quiz_id):
    """Delete a quiz with proper confirmation"""
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            quiz = get_object_or_404(Quiz, id=quiz_id)
            quiz_title = quiz.title
            
            # Store attempt count for message
            attempt_count = quiz.attempts.count()
            
            # Delete the quiz (this will cascade to questions, choices, and attempts)
            quiz.delete()
            
            if attempt_count > 0:
                messages.success(request, f'✅ Quiz "{quiz_title}" deleted successfully! {attempt_count} attempt(s) were also removed.')
            else:
                messages.success(request, f'✅ Quiz "{quiz_title}" deleted successfully!')
                
        except Quiz.DoesNotExist:
            messages.error(request, '❌ Quiz not found!')
        except Exception as e:
            messages.error(request, f'❌ Error deleting quiz: {str(e)}')
    
    return redirect('admin_quizzes')


@login_required
def performance(request):
    return render(request, 'performance.html')


@login_required
def performance_data(request):
    """Provide performance data for both courses and quizzes - Professional version with retake tracking"""
    student = request.user

    try:
        # Get course data
        enrolled_courses = StudentCourse.objects.filter(student=student).select_related('course')
        courses_data = []
        
        total_courses = enrolled_courses.count()
        completed_courses = 0
        total_progress = 0

        for sc in enrolled_courses:
            progress, watched_videos, total_videos = calculate_course_progress(sc)
            total_progress += progress
            
            is_completed = sc.completed or progress >= 95
            if is_completed:
                completed_courses += 1

            courses_data.append({
                "name": sc.course.course_name,
                "progress": progress,
                "completed": is_completed,
                "watched_videos": watched_videos,
                "total_videos": total_videos
            })

        # Get UNIQUE quizzes with their latest attempt data
        completed_quiz_ids = QuizAttempt.objects.filter(
            student=student, 
            is_completed=True
        ).values_list('quiz_id', flat=True).distinct()
        
        completed_quizzes = completed_quiz_ids.count()
        
        # Get quiz data for display - professional format with retake tracking
        quizzes_data = []
        total_quiz_score = 0
        quiz_count_with_score = 0
        total_retakes = 0
        
        for quiz_id in completed_quiz_ids:
            # Get all attempts for this quiz
            all_attempts = QuizAttempt.objects.filter(
                student=student, 
                quiz_id=quiz_id, 
                is_completed=True
            ).select_related('quiz', 'quiz__course').order_by('completed_at')
            
            if all_attempts.exists():
                total_attempts = all_attempts.count()
                latest_attempt = all_attempts.last()
                first_attempt = all_attempts.first()
                best_attempt = all_attempts.order_by('-score').first()
                
                # Count retakes (excluding first attempt)
                retakes_for_quiz = total_attempts - 1
                total_retakes += retakes_for_quiz
                
                score = latest_attempt.score if latest_attempt.score is not None else 0
                best_score = best_attempt.score if best_attempt and best_attempt.score else score
                first_score = first_attempt.score if first_attempt and first_attempt.score else score

                if score > 0:
                    total_quiz_score += score
                    quiz_count_with_score += 1

                # Calculate time taken for latest attempt
                time_taken = "N/A"
                if latest_attempt.started_at and latest_attempt.completed_at:
                    time_diff = latest_attempt.completed_at - latest_attempt.started_at
                    total_seconds = int(time_diff.total_seconds())
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    time_taken = f"{minutes}m {seconds}s"

                quizzes_data.append({
                    "id": quiz_id,
                    "title": latest_attempt.quiz.title,
                    "score": score,
                    "best_score": best_score,
                    "first_score": first_score,
                    "passing_score": latest_attempt.quiz.passing_score,
                    "course": latest_attempt.quiz.course.course_name,
                    "total_attempts": total_attempts,
                    "time_taken": time_taken,
                    "completed_at": latest_attempt.completed_at.strftime("%b %d, %Y") if latest_attempt.completed_at else "N/A",
                    "is_passed": score >= latest_attempt.quiz.passing_score,
                    "status": "Passed" if score >= latest_attempt.quiz.passing_score else "Failed"
                })

        # Sort quizzes by completion date (newest first)
        quizzes_data.sort(key=lambda x: x.get('completed_at', ''), reverse=True)

        # Calculate averages
        avg_course_progress = round(total_progress / total_courses, 1) if total_courses > 0 else 0
        avg_quiz_score = round(total_quiz_score / quiz_count_with_score, 1) if quiz_count_with_score > 0 else 0

        data = {
            'courses': courses_data,
            'quizzes': quizzes_data,
            'overview': {
                'completed_courses': completed_courses,
                'in_progress_courses': total_courses - completed_courses,
                'completed_quizzes': completed_quizzes,
                'quiz_retakes': total_retakes,
                'total_courses': total_courses,
                'avg_course_progress': avg_course_progress,
                'avg_quiz_score': avg_quiz_score
            }
        }

        return JsonResponse(data)

    except Exception as e:
        print(f"Error in performance_data: {str(e)}")
        
        return JsonResponse({
            'courses': [],
            'quizzes': [],
            'overview': {
                'completed_courses': 0,
                'in_progress_courses': 0,
                'completed_quizzes': 0,
                'quiz_retakes': 0,
                'total_courses': 0,
                'avg_course_progress': 0,
                'avg_quiz_score': 0
            }
        })


# Add these imports at the top of views.py if not already present


# Add these recommendation views to your existing views.py


@login_required
def recommendations(request):
    """AI-powered recommendations based on student's courses and quizzes"""
    if not request.user.is_authenticated:
        return redirect('student_login')
    
    student = request.user

    # Get student's enrolled courses with progress (same as dashboard)
    enrolled_courses = StudentCourse.objects.filter(student=student).select_related('course').prefetch_related('video_progress', 'course__videos')

    courses_progress = []
    total_courses = enrolled_courses.count()
    completed_courses = 0
    in_progress_courses = 0

    for sc in enrolled_courses:
        total_videos = sc.course.videos.count()
        watched_videos = sc.video_progress.filter(watched=True).count()
        progress = int((watched_videos / total_videos) * 100) if total_videos > 0 else 0

        if sc.completed or progress == 100:
            completed_courses += 1
        else:
            in_progress_courses += 1

        courses_progress.append({
            'student_course': sc,
            'progress': progress,
            'total_videos': total_videos,
            'watched_videos': watched_videos,
        })

    # Get quiz data from dashboard helper
    quiz_data = update_student_dashboard_with_quizzes(request)
    
    # Generate simple AI recommendations based on current data
    ai_recommendations = generate_simple_recommendations(student, courses_progress, quiz_data)
    
    context = {
        'user': student,
        'courses_progress': courses_progress,
        'total_courses': total_courses,
        'completed_courses': completed_courses,
        'in_progress_courses': in_progress_courses,
        'total_pending_quizzes': quiz_data['total_pending_quizzes'],
        'ai_recommendations': ai_recommendations,
    }
    
    return render(request, 'recommendations.html', context)

def generate_simple_recommendations(student, courses_progress, quiz_data):
    """Generate simple AI recommendations without database models"""
    recommendations = []
    
    # Analyze course progress for recommendations
    for course_data in courses_progress:
        sc = course_data['student_course']
        progress = course_data['progress']
        course_name = sc.course.course_name
        
        # Completed course
        if progress == 100:
            recommendations.append({
                'type': 'completed',
                'title': 'Great work! 🎉',
                'message': f"You've completed '{course_name}'. Consider exploring advanced or related courses next.",
                'priority': 1,
                'icon': '✅',
                'color': 'green'
            })
        
        # High progress (75-99%)
        elif 75 <= progress < 100:
            recommendations.append({
                'type': 'almost_done',
                'title': 'You\'re almost there! 🎯',
                'message': f"You've completed {progress}% of '{course_name}'. Just a little more to complete the course!",
                'priority': 2,
                'icon': '🏆',
                'color': 'blue'
            })
        
        # Slow progress (20-75%)
        elif 20 <= progress < 75:
            recommendations.append({
                'type': 'keep_going',
                'title': 'Keep the momentum! ⏱️',
                'message': f"You've made progress in '{course_name}' ({progress}%). Try watching 1-2 videos daily to stay consistent.",
                'priority': 3,
                'icon': '📈',
                'color': 'amber'
            })
        
        # Just started (1-20%)
        elif 0 < progress < 20:
            recommendations.append({
                'type': 'good_start',
                'title': 'Good start! 🚀',
                'message': f"You've made a small start in '{course_name}' ({progress}%). Try watching 1-2 videos daily to stay consistent.",
                'priority': 4,
                'icon': '🎯',
                'color': 'amber'
            })
        
        # Not started
        elif progress == 0:
            recommendations.append({
                'type': 'not_started',
                'title': 'Ready to begin? 📚',
                'message': f"You haven't started '{course_name}' yet. Begin with the first video to kick off your progress!",
                'priority': 5,
                'icon': '🎯',
                'color': 'blue'
            })
    
    # Analyze quiz performance
    if quiz_data.get('recent_attempts'):
        for attempt in quiz_data['recent_attempts'][:3]:  # Last 3 attempts
            if attempt.score >= 85:
                recommendations.append({
                    'type': 'quiz_excellent',
                    'title': 'Excellent quiz performance! 🌟',
                    'message': f"You scored {attempt.score:.1f}% on '{attempt.quiz.title}'. Your understanding is strong!",
                    'priority': 2,
                    'icon': '🏆',
                    'color': 'green'
                })
            elif attempt.score < 70:
                recommendations.append({
                    'type': 'quiz_review',
                    'title': 'Time for review 📚',
                    'message': f"You scored {attempt.score:.1f}% on '{attempt.quiz.title}'. Consider reviewing the materials.",
                    'priority': 4,
                    'icon': '📖',
                    'color': 'red'
                })
    
    # Pending quizzes alert
    if quiz_data.get('total_pending_quizzes', 0) > 0:
        recommendations.append({
            'type': 'pending_quizzes',
            'title': 'Pending quizzes alert! 📝',
            'message': f"You have {quiz_data['total_pending_quizzes']} pending quiz{'zes' if quiz_data['total_pending_quizzes'] > 1 else ''} to complete.",
            'priority': 3,
            'icon': '⏰',
            'color': 'amber'
        })
    
    # Study consistency based on course progress
    active_courses = len([cp for cp in courses_progress if cp['progress'] > 0])
    if active_courses >= 3:
        recommendations.append({
            'type': 'active_learner',
            'title': 'Active learner! 📅',
            'message': f'You\'re actively working on {active_courses} courses. Great consistency!',
            'priority': 2,
            'icon': '⭐',
            'color': 'green'
        })
    
    # Sort by priority (lower number = higher priority)
    recommendations.sort(key=lambda x: x['priority'])
    
    return recommendations


    
# Student Settings
# ----------------------------
@login_required
def settings(request):
    user = request.user
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password and password != confirm_password:
            return JsonResponse({"error": "Passwords do not match"}, status=400)

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        if password:
            user.set_password(password)
        user.save()
        update_session_auth_hash(request, user)

        return JsonResponse({
            "message": "Settings updated successfully",
            "user": {"first_name": user.first_name, "last_name": user.last_name, "email": user.email}
        })

    return render(request, 'settings.html', {'user': user})


# ----------------------------
# Admin Authentication
# ----------------------------
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user and user.user_type == 'admin':
            login(request, user)
            return redirect('admin_dashboard')
        messages.error(request, "Invalid admin credentials.")
    return render(request, 'admin_login.html')


def admin_signup(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('admin_signup')

        if BaseUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('admin_signup')

        if BaseUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect('admin_signup')

        admin_user = BaseUser.objects.create_user(
            username=username, 
            email=email, 
            password=password,
            first_name=first_name,
            last_name=last_name,
            user_type='admin'
        )
        admin_user.is_admin_user = True
        admin_user.save()
        messages.success(request, "Admin account created! Please login.")
        return redirect('admin_login')

    return render(request, 'admin_register.html')


@login_required
def admin_logout(request):
    logout(request)
    return redirect('admin_login')


# ----------------------------
# Admin Dashboard & Students
# ----------------------------
# ----------------------------
# Admin Dashboard & Students
# ----------------------------
@login_required
def admin_dashboard(request):
    """Admin dashboard - main view"""
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')
    
    # Add current date and time to context
    from django.utils import timezone
    current_time = timezone.now()
    
    context = {
        'current_date': current_time.strftime('%B %d, %Y'),
        'current_time': current_time.strftime('%I:%M %p')
    }
    
    return render(request, 'admin_dashboard.html', context)

@login_required
def admin_dashboard_data(request):
    """Admin dashboard data - shows all students from database"""
    if not request.user.user_type == 'admin':
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        # Get ALL students from database (not just those with courses)
        all_students = BaseUser.objects.filter(user_type='student')
        total_students = all_students.count()
        
        # Get total courses
        total_courses = Course.objects.count()
        
        # Get pending assignments (students with no courses assigned)
        students_without_courses = BaseUser.objects.filter(
            user_type='student'
        ).exclude(
            id__in=StudentCourse.objects.values('student_id')
        ).count()
        
        # Enhanced user study data showing ALL students
        user_study_data = []
        
        for student in all_students:
            try:
                # Get student's course assignments (if any)
                student_courses = StudentCourse.objects.filter(student=student).select_related('course')
                
                if student_courses.exists():
                    # Student has courses - show each course assignment
                    for sc in student_courses:
                        # Calculate progress using your existing function
                        progress, watched_videos, total_videos = calculate_course_progress(sc)
                        
                        # Calculate study time - estimate based on videos watched
                        total_watch_time_minutes = watched_videos * 10  # 10 minutes per video estimate
                        
                        # Get course duration
                        course_duration = "4 weeks"  # Default fallback
                        if hasattr(sc.course, 'duration') and sc.course.duration:
                            course_duration = f"{sc.course.duration} weeks"
                        elif hasattr(sc.course, 'duration_weeks') and sc.course.duration_weeks:
                            course_duration = f"{sc.course.duration_weeks} weeks"
                        else:
                            # Estimate based on video count
                            estimated_weeks = max(1, total_videos // 5)  # ~5 videos per week
                            course_duration = f"{estimated_weeks} weeks"
                        
                        # Determine status based on progress
                        if sc.completed or progress >= 95:
                            status = "completed"
                            status_display = "Completed"
                        elif progress > 0:
                            status = "in_progress"
                            status_display = "In Progress"
                        else:
                            status = "not_started"
                            status_display = "Not Started"
                        
                        user_study_data.append({
                            'username': getattr(student, 'username', 'Unknown'),
                            'email': getattr(student, 'email', 'No email'),
                            'course_name': getattr(sc.course, 'course_name', 'Unknown Course'),
                            'duration': course_duration,
                            'study_time': total_watch_time_minutes,
                            'progress': progress,
                            'status': status,
                            'status_display': status_display,
                            'watched_videos': watched_videos,
                            'total_videos': total_videos,
                            'start_date': sc.start_date.strftime('%Y-%m-%d') if sc.start_date else 'Not set',
                            'end_date': sc.end_date.strftime('%Y-%m-%d') if sc.end_date else 'Not set',
                            'last_activity': sc.enrolled_at.strftime('%Y-%m-%d') if sc.enrolled_at else 'Never',
                            'has_courses': True
                        })
                else:
                    # Student has NO courses assigned - show them as "No Courses"
                    user_study_data.append({
                        'username': getattr(student, 'username', 'Unknown'),
                        'email': getattr(student, 'email', 'No email'),
                        'course_name': 'No Course Assigned',
                        'duration': 'N/A',
                        'study_time': 0,
                        'progress': 0,
                        'status': 'not_started',
                        'status_display': 'No Courses',
                        'watched_videos': 0,
                        'total_videos': 0,
                        'start_date': 'Not set',
                        'end_date': 'Not set',
                        'last_activity': 'Never',
                        'has_courses': False
                    })
                
            except Exception as e:
                print(f"Error processing student {student.id}: {str(e)}")
                # Add minimal fallback data for this student
                user_study_data.append({
                    'username': getattr(student, 'username', 'Unknown'),
                    'email': getattr(student, 'email', 'No email'),
                    'course_name': 'Error Loading Data',
                    'duration': 'N/A',
                    'study_time': 0,
                    'progress': 0,
                    'status': 'not_started',
                    'status_display': 'Error',
                    'watched_videos': 0,
                    'total_videos': 0,
                    'start_date': 'Not set',
                    'end_date': 'Not set',
                    'last_activity': 'Never',
                    'has_courses': False
                })
                continue

        # Calculate system health
        system_health = calculate_system_health()

        data = {
            'total_students': total_students,
            'total_courses': total_courses,
            'pending_assignments': students_without_courses,
            'system_health': system_health,
            'user_study_data': user_study_data,
        }

        return JsonResponse(data)

    except Exception as e:
        print(f"Error in admin_dashboard_data: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return safe default data
        return JsonResponse({
            'total_students': 0,
            'total_courses': 0,
            'pending_assignments': 0,
            'system_health': 0,
            'user_study_data': [],
            'error': str(e)
        })

def calculate_system_health():
    """Calculate system health based on various metrics"""
    try:
        health_score = 100
        
        # Check database connectivity
        try:
            BaseUser.objects.count()
        except:
            health_score -= 30
        
        # Check if there are courses
        course_count = Course.objects.count()
        if course_count == 0:
            health_score -= 10
        
        # Check if there are students
        student_count = BaseUser.objects.filter(user_type='student').count()
        if student_count == 0:
            health_score -= 10
            
        # Check for recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_enrollments = StudentCourse.objects.filter(enrolled_at__gte=week_ago).count()
        if recent_enrollments == 0 and student_count > 0:
            health_score -= 5
            
        return max(0, health_score)  # Ensure non-negative
        
    except Exception:
        return 80  # Default fallback
# Admin Courses
# ----------------------------
@login_required
def admin_courses(request):
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')

    courses = Course.objects.all()
    add_form = CourseForm(request.POST or None, request.FILES or None)

    if request.method == 'POST':
        if add_form.is_valid():
            # Save the course instance
            course = add_form.save(commit=False)
            course.save()

            # Handle YouTube links
            youtube_links = add_form.cleaned_data.get('youtube_links', [])
            for idx, url in enumerate(youtube_links, start=1):
                Video.objects.create(
                    course=course,
                    title=f"Video {idx}",
                    youtube_url=url,
                    order=idx
                )

            messages.success(request, "Course added successfully with videos!")
            return redirect('admin_courses')
        else:
            messages.error(request, f"Error adding course: {add_form.errors}")

    return render(request, 'admin_courses.html', {'courses': courses, 'add_form': add_form})


# ----------------------------
# Add Course
# ----------------------------
# views.py - Update the add_course function
@login_required
def add_course(request):
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')

    form = CourseForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            # Save Course instance
            course = form.save(commit=False)
            course.save()

            # Create Video objects from YouTube URLs with custom titles
            youtube_links = form.cleaned_data.get('youtube_links', [])
            video_titles = form.cleaned_data.get('video_titles', [])
            
            for idx, url in enumerate(youtube_links, start=1):
                # Use custom title if provided, otherwise generate a default one
                if video_titles and idx <= len(video_titles):
                    title = video_titles[idx-1]
                else:
                    title = f"{course.course_name} - Video {idx}"
                
                Video.objects.create(
                    course=course,
                    title=title,
                    youtube_url=url,
                    order=idx
                )

            messages.success(request, "Course added successfully with videos!")
            return redirect('admin_courses')
        else:
            messages.error(request, f"Error adding course: {form.errors}")

    # FIX THIS LINE - Remove the duplicate part
    return render(request, 'admin_courses_form.html', {'form': form, 'action': 'Add'})


# Edit Course
# ----------------------------
# views.py - Update the edit_course function
@login_required
def edit_course(request, course_id):
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')

    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            course = form.save(commit=False)
            course.save()

            # Remove old videos
            course.videos.all().delete()

            # Add new videos with custom titles
            youtube_links = form.cleaned_data.get('youtube_links', [])
            video_titles = form.cleaned_data.get('video_titles', [])
            
            for idx, url in enumerate(youtube_links, start=1):
                # Use custom title if provided, otherwise generate a default one
                if video_titles and idx <= len(video_titles):
                    title = video_titles[idx-1]
                else:
                    title = f"{course.course_name} - Video {idx}"
                
                Video.objects.create(
                    course=course,
                    title=title,
                    youtube_url=url,
                    order=idx
                )

            messages.success(request, "Course updated successfully!")
            return redirect('admin_courses')
        else:
            messages.error(request, f"Error updating course: {form.errors}")
    else:
        # Prepopulate textarea with comma-separated URLs and titles
        videos = course.videos.all()
        initial_links = ",".join([v.youtube_url for v in videos])
        initial_titles = ",".join([v.title for v in videos])
        form = CourseForm(instance=course, initial={
            'youtube_links': initial_links,
            'video_titles': initial_titles
        })

    return render(request, 'admin_courses_form.html', {'form': form, 'action': 'Edit', 'course': course})


@login_required
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == "POST":
        course.delete()
        messages.success(request, f"Course '{course.course_name}' deleted successfully!")
        return redirect('admin_courses')
    return redirect('admin_courses')


# ----------------------------
# Admin Students
# ----------------------------

# ----------------------------
# Admin Students
# ----------------------------
@login_required
def admin_students(request):
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')

    # Get all students
    students = BaseUser.objects.filter(user_type='student')
    
    # Calculate study progress for each student
    students_with_progress = []
    total_progress_sum = 0
    active_students_count = 0
    
    for student in students:
        student_courses = StudentCourse.objects.filter(student=student)
        total_videos = 0
        watched_videos = 0
        
        for sc in student_courses:
            course_videos = sc.course.videos.count()
            total_videos += course_videos
            watched_videos += sc.video_progress.filter(watched=True).count()
        
        # Calculate progress
        study_progress = int((watched_videos / total_videos) * 100) if total_videos > 0 else 0
        total_progress_sum += study_progress
        
        # Count active students (those with any progress)
        if study_progress > 0:
            active_students_count += 1
        
        students_with_progress.append({
            'student': student,
            'study_progress': study_progress,
            'total_courses': student_courses.count(),
            'watched_videos': watched_videos,
            'total_videos': total_videos
        })

    # Calculate statistics
    total_students = students.count()
    average_progress = total_progress_sum // total_students if total_students > 0 else 0
    
    # Calculate new students this week
    one_week_ago = timezone.now() - timedelta(days=7)
    new_this_week = BaseUser.objects.filter(
        user_type='student',
        date_joined__gte=one_week_ago
    ).count()

    context = {
        'students_with_progress': students_with_progress,
        'user': request.user,
        'total_students': total_students,
        'active_students': active_students_count,
        'average_progress': average_progress,
        'new_this_week': new_this_week,
    }

    return render(request, 'admin_students.html', context)             
#---


@login_required
@user_passes_test(is_admin)
def get_student_details(request, id):
    """API endpoint to get detailed student information"""
    if not request.user.user_type == 'admin':
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        student = BaseUser.objects.get(id=id, user_type='student')
        
        # Get student's enrolled courses with progress
        enrolled_courses = StudentCourse.objects.filter(student=student).select_related('course')
        courses_data = []
        
        total_watched_videos = 0
        total_videos_all = 0
        
        for sc in enrolled_courses:
            progress, watched_videos, total_videos = calculate_course_progress(sc)
            total_watched_videos += watched_videos
            total_videos_all += total_videos
            
            courses_data.append({
                'course_name': sc.course.course_name,
                'progress': progress,
                'watched_videos': watched_videos,
                'total_videos': total_videos,
                'completed': sc.completed,
                'enrolled_date': sc.enrolled_at.strftime('%Y-%m-%d') if sc.enrolled_at else 'Not set',
                'status': 'Completed' if sc.completed else 'In Progress'
            })

        # Calculate overall statistics
        total_courses = enrolled_courses.count()
        completed_courses = enrolled_courses.filter(completed=True).count()
        
        # Calculate overall progress
        overall_progress = int((total_watched_videos / total_videos_all) * 100) if total_videos_all > 0 else 0
        
        # Calculate total study time (estimate: 10 minutes per video)
        total_study_time_minutes = total_watched_videos * 10
        total_study_time_hours = round(total_study_time_minutes / 60, 1)

        # Prepare comprehensive student data
        student_data = {
            'id': student.id,
            'username': student.username,
            'email': student.email,
            'first_name': student.first_name or '',
            'last_name': student.last_name or '',
            'full_name': f"{student.first_name} {student.last_name}".strip() or student.username,
            'date_joined': student.date_joined.strftime('%B %d, %Y'),
            'last_login': student.last_login.strftime('%B %d, %Y at %I:%M %p') if student.last_login else 'Never',
            'is_active': student.is_active,
            
            # Statistics
            'enrolled_courses_count': total_courses,
            'completed_courses_count': completed_courses,
            'in_progress_courses_count': total_courses - completed_courses,
            'overall_progress': overall_progress,
            'total_videos_watched': total_watched_videos,
            'total_study_time_minutes': total_study_time_minutes,
            'total_study_time_hours': total_study_time_hours,
            
            # Course details
            'enrolled_courses': courses_data
        }
        
        return JsonResponse(student_data)
        
    except BaseUser.DoesNotExist:
        return JsonResponse({"error": "Student not found"}, status=404)
    except Exception as e:
        import traceback
        print(f"Error in get_student_details: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)
    




@login_required
def admin_analytics(request):
    return render(request, 'admin_analytics.html')



@login_required
def admin_analytics_data(request):
    """Fixed analytics data endpoint that matches your models"""
    if not request.user.user_type == 'admin':
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        today = timezone.now().date()
        
        # Student metrics - FIXED: Using correct model relationships
        total_students = BaseUser.objects.filter(user_type='student').count()
        
        # New students this week
        one_week_ago = today - timedelta(days=7)
        new_students = BaseUser.objects.filter(
            user_type='student', 
            date_joined__date__gte=one_week_ago
        ).count()
        
        # Active students (students with any course activity)
        # Since we don't have last_accessed field, we'll use students with enrollments
        active_students = StudentCourse.objects.values('student').distinct().count()

        # Course metrics
        total_courses = Course.objects.count()
        total_enrollments = StudentCourse.objects.count()
        completed_courses = StudentCourse.objects.filter(completed=True).count()
        
        # Calculate average progress
        all_student_courses = StudentCourse.objects.all()
        total_progress = 0
        valid_courses = 0
        
        for sc in all_student_courses:
            try:
                progress, watched_videos, total_videos = calculate_course_progress(sc)
                if total_videos > 0:
                    total_progress += progress
                    valid_courses += 1
            except Exception as e:
                print(f"Error calculating progress for student course {sc.id}: {e}")
                continue
        
        avg_progress = round(total_progress / valid_courses, 1) if valid_courses > 0 else 0

        # Weekly student registration trend (last 8 weeks)
        weekly_data = []
        for i in range(8):
            week_end = today - timedelta(weeks=i)
            week_start = week_end - timedelta(days=6)
            
            students_count = BaseUser.objects.filter(
                user_type='student',
                date_joined__date__range=[week_start, week_end]
            ).count()

            weekly_data.append({
                'week': f"W{8-i}",
                'students': students_count,
            })
        
        # Reverse to show chronological order
        weekly_data.reverse()

        # Course popularity (top courses by enrollment)
        popular_courses = Course.objects.annotate(
            enrollment_count=Count('studentcourse')
        ).order_by('-enrollment_count')[:5]
        
        course_data = {
            'labels': [course.course_name for course in popular_courses],
            'enrollments': [course.enrollment_count for course in popular_courses]
        }

        # Progress distribution - FIXED: Using correct field names
        progress_distribution = {
            'completed': StudentCourse.objects.filter(completed=True).count(),
            'in_progress': StudentCourse.objects.filter(
                completed=False
            ).exclude(
                video_progress__isnull=True
            ).distinct().count(),
            'not_started': StudentCourse.objects.filter(
                completed=False,
                video_progress__isnull=True
            ).distinct().count()
        }

        # Calculate rates with safe division
        completion_rate = round((completed_courses / total_enrollments * 100), 1) if total_enrollments > 0 else 0
        active_rate = round((active_students / total_students * 100), 1) if total_students > 0 else 0

        data = {
            # Key metrics
            'new_students': new_students,
            'total_students': total_students,
            'active_students': active_students,
            'total_courses': total_courses,
            'total_enrollments': total_enrollments,
            'completed_courses': completed_courses,
            'avg_progress': avg_progress,
            'completion_rate': completion_rate,
            'active_rate': active_rate,
            
            # Chart data
            'weekly_data': weekly_data,
            'course_data': course_data,
            'progress_distribution': progress_distribution,
            
            'error': None
        }

        print(f"DEBUG: Analytics data prepared successfully")
        return JsonResponse(data)

    except Exception as e:
        print(f"ERROR in admin_analytics_data: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return safe fallback data
        return JsonResponse({
            'error': str(e),
            'new_students': 0,
            'total_students': 0,
            'active_students': 0,
            'total_courses': 0,
            'total_enrollments': 0,
            'completed_courses': 0,
            'avg_progress': 0,
            'completion_rate': 0,
            'active_rate': 0,
            'weekly_data': [{'week': f'W{i+1}', 'students': 0} for i in range(8)],
            'course_data': {'labels': [], 'enrollments': []},
            'progress_distribution': {'completed': 0, 'in_progress': 0, 'not_started': 0}
        }, status=500)
    

@login_required
def admin_settings(request):
    return render(request, 'admin_settings.html')


# ----------------------------
# Error Pages
# ----------------------------
def page_not_found(request, exception):
    return render(request, '404.html', status=404)


def server_error(request):
    return render(request, '500.html', status=500)


@login_required
@csrf_exempt
def update_video_progress(request):
    import json
    if request.method == "POST":
        data = json.loads(request.body)
        student_course = get_object_or_404(StudentCourse, id=data["student_course_id"], student=request.user)
        video = get_object_or_404(Video, id=data["video_id"])
        current_time = data.get("current_time", 0)
        duration = data.get("duration", 0)

        progress, _ = StudentVideoProgress.objects.get_or_create(student_course=student_course, video=video)
        progress.last_watched_time = current_time
        if duration > 0 and current_time / duration >= 0.95:
            progress.mark_watched()

            # Mark course completed if all videos watched
            total_videos = student_course.course.videos.count()
            watched_videos = student_course.video_progress.filter(watched=True).count()
            if watched_videos == total_videos:
                student_course.mark_completed()
        progress.save()

        return JsonResponse({"status": "success"})


def calculate_course_progress(student_course):
    """Calculate course progress for a student with error handling"""
    try:
        if not student_course or not student_course.course:
            return 0, 0, 0
            
        total_videos = student_course.course.videos.count()
        if total_videos == 0:
            return 0, 0, 0
            
        # Use the video_progress relationship to count watched videos
        watched_videos = student_course.video_progress.filter(watched=True).count()
        progress = int((watched_videos / total_videos) * 100)
        
        return progress, watched_videos, total_videos
        
    except Exception as e:
        print(f"Error calculating progress for student course {getattr(student_course, 'id', 'unknown')}: {str(e)}")
        return 0, 0, 0
# ============================================================================
# MILESTONE 3: Course Assignment System
# ============================================================================
@login_required
@user_passes_test(is_admin)
def assign_courses(request):
    """Professional course assignment system"""
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')
    
    # FIXED: Use user_type instead of is_admin_user
    students = BaseUser.objects.filter(user_type='student').order_by('username')
    courses = Course.objects.all().order_by('course_name')
    
    # Get current assignments with detailed information
    student_assignments = {}
    for student in students:
        enrolled_courses = StudentCourse.objects.filter(student=student).select_related('course')
        student_assignments[student.id] = {
            'courses': list(enrolled_courses.values_list('course_id', flat=True)),
            'email': student.email,
            'username': student.username,
            'assignments': [
                {
                    'course_id': sc.course_id,
                    'course_name': sc.course.course_name,
                    'start_date': sc.start_date.isoformat() if sc.start_date else None,
                    'end_date': sc.end_date.isoformat() if sc.end_date else None,
                    'status': sc.status,
                    'priority': sc.priority
                }
                for sc in enrolled_courses
            ]
        }
    
    context = {
        'students': students,
        'courses': courses,
        'student_assignments': json.dumps(student_assignments),
        'today': timezone.now().date().isoformat(),
        'max_date': (timezone.now() + timedelta(days=365)).date().isoformat()  # 1 year from now
    }
    
    return render(request, 'assign_courses.html', context)


@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_POST
def save_course_assignments(request):
    """Save professional course assignments with all details"""
    if not request.user.user_type == 'admin':
        return JsonResponse({'success': False, 'error': 'Unauthorized access'})
    
    try:
        print("=== DEBUG: save_course_assignments called ===")
        data = json.loads(request.body)
        student_id = data.get('student_id')
        assignments = data.get('assignments', [])
        
        print(f"DEBUG: Student ID: {student_id}")
        print(f"DEBUG: Assignments count: {len(assignments)}")
        print(f"DEBUG: Assignments data: {assignments}")
        
        if not student_id:
            return JsonResponse({'success': False, 'error': 'Student ID is required'})
        
        if not assignments:
            return JsonResponse({'success': False, 'error': 'No assignments provided'})
        
        # Get student
        try:
            student = BaseUser.objects.get(id=student_id, user_type='student')
            print(f"DEBUG: Found student: {student.username}")
        except BaseUser.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Student not found'})
        
        assigned_courses = []
        validation_errors = []
        
        # Process each assignment
        for assignment in assignments:
            course_id = assignment.get('course_id')
            start_date_str = assignment.get('start_date')
            end_date_str = assignment.get('end_date')
            priority = assignment.get('priority', 'medium')
            notes = assignment.get('notes', '')
            
            print(f"DEBUG: Processing course {course_id} - {start_date_str} to {end_date_str}")
            
            # Validate required fields
            if not course_id:
                validation_errors.append("Course ID is required for each assignment")
                continue
            
            if not start_date_str:
                validation_errors.append("Start date is required for each course")
                continue
            
            if not end_date_str:
                validation_errors.append("End date is required for each course")
                continue
            
            try:
                # Get course
                course = Course.objects.get(id=course_id)
                print(f"DEBUG: Found course: {course.course_name}")
                
                # Parse dates using timezone
                start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date()
                today = timezone.now().date()
                
                print(f"DEBUG: Parsed dates - Start: {start_date}, End: {end_date}, Today: {today}")
                
                # Validate dates
                if start_date >= end_date:
                    validation_errors.append(f"End date must be after start date for '{course.course_name}'")
                    continue
                
                if start_date < today:
                    validation_errors.append(f"Start date cannot be in the past for '{course.course_name}'")
                    continue
                
                # Check if this course is already assigned to the student
                existing_assignment = StudentCourse.objects.filter(
                    student=student, 
                    course=course
                ).first()
                
                if existing_assignment:
                    # Update existing assignment
                    existing_assignment.start_date = start_date
                    existing_assignment.end_date = end_date
                    existing_assignment.target_completion_date = end_date
                    existing_assignment.priority = priority
                    existing_assignment.notes = notes
                    existing_assignment.status = 'not_started'
                    existing_assignment.save()
                    student_course = existing_assignment
                    print(f"DEBUG: Updated existing assignment for {course.course_name}")
                else:
                    # Create new student course assignment
                    student_course = StudentCourse.objects.create(
                        student=student,
                        course=course,
                        start_date=start_date,
                        end_date=end_date,
                        target_completion_date=end_date,
                        priority=priority,
                        notes=notes,
                        status='not_started',
                        completed=False,
                        enrolled_at=timezone.now()
                    )
                    print(f"DEBUG: Created new assignment for {course.course_name}")
                
                # Create or update video progress entries
                videos = course.videos.all()
                for video in videos:
                    progress, created = StudentVideoProgress.objects.get_or_create(
                        student_course=student_course,
                        video=video,
                        defaults={
                            'watched': False,
                            'last_watched_time': 0.0
                        }
                    )
                    if created:
                        print(f"DEBUG: Created video progress for video {video.id}")
                
                assigned_courses.append({
                    'name': course.course_name,
                    'start_date': start_date_str,
                    'end_date': end_date_str,
                    'priority': priority
                })
                print(f"DEBUG: Successfully processed {course.course_name}")
                
            except Course.DoesNotExist:
                validation_errors.append(f"Course with ID {course_id} not found")
            except ValueError as e:
                validation_errors.append(f"Invalid date format for course '{course.course_name}': {str(e)}")
            except Exception as e:
                validation_errors.append(f"Error processing course {course_id}: {str(e)}")
                print(f"DEBUG: Error processing course {course_id}: {str(e)}")
        
        # Check if we have validation errors
        if validation_errors:
            print(f"DEBUG: Validation errors: {validation_errors}")
            return JsonResponse({
                'success': False, 
                'error': 'Validation errors occurred',
                'details': validation_errors
            })
        
        if not assigned_courses:
            return JsonResponse({'success': False, 'error': 'No valid courses were assigned'})
        
        print(f"DEBUG: Successfully assigned {len(assigned_courses)} courses to {student.username}")
        print(f"DEBUG: Assigned courses: {assigned_courses}")
        
        return JsonResponse({
            'success': True, 
            'message': f'Successfully assigned {len(assigned_courses)} courses to {student.username}',
            'assigned_courses': assigned_courses,
            'student_name': student.username
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        print(f"DEBUG: Unexpected error in save_course_assignments: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})



def student_study_tracks(request):
    """View all student study tracks"""
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')
    
    students = BaseUser.objects.filter(user_type='student')
    
    study_tracks = []
    for student in students:
        enrollments = StudentCourse.objects.filter(student=student).select_related('course')
        
        enrollment_data = []
        total_progress = 0
        for enrollment in enrollments:
            progress, watched_videos, total_videos = calculate_course_progress(enrollment)
            total_progress += progress
            
            enrollment_data.append({
                'enrollment': enrollment,
                'progress': progress,
                'watched_videos': watched_videos,
                'total_videos': total_videos,
                'course': enrollment.course
            })
        
        avg_progress = total_progress / len(enrollments) if enrollments else 0
        
        study_tracks.append({
            'student': student,
            'enrollments': enrollment_data,
            'total_courses': enrollments.count(),
            'avg_progress': avg_progress
        })
    
    return render(request, 'student_study_tracks.html', {
        'study_tracks': study_tracks
    })

# ============================================================================
# Enhanced Admin Dashboard for Milestone 3
# ============================================================================




@login_required
def admin_profile_settings(request):
    """Admin profile settings page"""
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')
    
    if request.method == 'POST':
        user = request.user
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        
        messages.success(request, "Profile updated successfully!")
        return redirect('admin_profile_settings')
    
    return render(request, 'admin_profile_settings.html')


@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_POST
def admin_add_student(request):
    """API endpoint to add a new student"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        
        # Validation
        if not all([username, email, password, first_name, last_name]):
            return JsonResponse({'success': False, 'error': 'All fields are required'})
        
        if len(password) < 8:
            return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters'})
        
        if BaseUser.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': 'Username already exists'})
        
        if BaseUser.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Email already exists'})
        
        # Create student user
        user = BaseUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            user_type='student'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Student {first_name} {last_name} created successfully!',
            'student_id': user.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_POST
def admin_edit_student(request):
    """API endpoint to edit a student"""
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        
        try:
            student = BaseUser.objects.get(id=student_id, user_type='student')
            
            # Check if username is taken by another user
            if BaseUser.objects.filter(username=username).exclude(id=student_id).exists():
                return JsonResponse({'success': False, 'error': 'Username already taken by another user'})
            
            # Check if email is taken by another user
            if BaseUser.objects.filter(email=email).exclude(id=student_id).exists():
                return JsonResponse({'success': False, 'error': 'Email already taken by another user'})
            
            # Update student
            student.username = username
            student.email = email
            student.first_name = first_name
            student.last_name = last_name
            
            # Update password if provided
            if password and len(password) >= 8:
                student.set_password(password)
            
            student.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Student {first_name} {last_name} updated successfully!'
            })
            
        except BaseUser.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Student not found'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_POST
def admin_delete_student(request):
    """API endpoint to delete a student"""
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        
        if not student_id:
            return JsonResponse({'success': False, 'error': 'Student ID is required'})
        
        try:
            student = BaseUser.objects.get(id=student_id, user_type='student')
            student_name = f"{student.first_name} {student.last_name}".strip() or student.username
            student.delete()
            
            return JsonResponse({
                'success': True, 
                'message': f'Student {student_name} deleted successfully'
            })
            
        except BaseUser.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Student not found'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    


                



# ============================================================================
# API Endpoints for Course Assignment System
# ============================================================================

@login_required
@user_passes_test(is_admin)
@csrf_exempt
def get_student_assignments_api(request, student_id):
    """API endpoint to get student assignments with current status"""
    if not request.user.user_type == 'admin':
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        student = get_object_or_404(BaseUser, id=student_id, user_type='student')
        assignments = StudentCourse.objects.filter(student=student).select_related('course')
        
        assignments_data = []
        for assignment in assignments:
            # Calculate current progress
            progress, watched_videos, total_videos = calculate_course_progress(assignment)
            
            # Determine status based on progress and dates
            current_status = assignment.status
            today = timezone.now().date()
            
            # Auto-update status based on progress
            if assignment.completed:
                current_status = 'completed'
            elif progress > 0 and progress < 100:
                current_status = 'in_progress'
            elif progress == 0 and assignment.start_date and today >= assignment.start_date:
                current_status = 'in_progress'
            elif progress == 0 and assignment.start_date and today < assignment.start_date:
                current_status = 'not_started'
            else:
                current_status = 'not_started'
            
            # Update the assignment status if it changed
            if assignment.status != current_status:
                assignment.status = current_status
                assignment.save()
            
            assignments_data.append({
                'id': assignment.id,
                'course_id': assignment.course.id,
                'course_name': assignment.course.course_name,
                'start_date': assignment.start_date.strftime('%Y-%m-%d') if assignment.start_date else None,
                'end_date': assignment.end_date.strftime('%Y-%m-%d') if assignment.end_date else None,
                'priority': assignment.priority,
                'status': current_status,
                'notes': assignment.notes or '',
                'progress': progress,
                'watched_videos': watched_videos,
                'total_videos': total_videos,
                'completed': assignment.completed,
                'enrolled_at': assignment.enrolled_at.strftime('%Y-%m-%d %H:%M') if assignment.enrolled_at else None
            })
        
        return JsonResponse({
            'success': True,
            'assignments': assignments_data,
            'student': {
                'id': student.id,
                'username': student.username,
                'email': student.email,
                'first_name': student.first_name,
                'last_name': student.last_name
            }
        })
        
    except Exception as e:
        print(f"Error in get_student_assignments_api: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_assignment_api(request, assignment_id):
    """API endpoint to delete a course assignment"""
    if not request.user.user_type == 'admin':
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        assignment = get_object_or_404(StudentCourse, id=assignment_id)
        course_name = assignment.course.course_name
        student_name = assignment.student.username
        
        # Delete the assignment
        assignment.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Assignment for "{course_name}" has been deleted successfully.'
        })
        
    except Exception as e:
        print(f"Error in delete_assignment_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
def update_assignment_api(request, assignment_id):
    """API endpoint to update a course assignment"""
    if not request.user.user_type == 'admin':
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        assignment = get_object_or_404(StudentCourse, id=assignment_id)
        data = json.loads(request.body)
        
        # Update fields
        if 'start_date' in data:
            assignment.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if 'end_date' in data:
            assignment.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        if 'priority' in data:
            assignment.priority = data['priority']
        if 'notes' in data:
            assignment.notes = data['notes']
        if 'status' in data:
            assignment.status = data['status']
            if data['status'] == 'completed':
                assignment.completed = True
                assignment.completed_at = timezone.now()
        
        assignment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Assignment updated successfully'
        })
        
    except Exception as e:
        print(f"Error in update_assignment_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
# ============================================================================
# MILESTONE 4 - TASK 2: QUIZ MANAGEMENT SYSTEM
# ============================================================================

@login_required
@user_passes_test(is_admin)
def admin_quizzes(request):
    """Quiz Management Dashboard"""
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')
    
    quizzes = Quiz.objects.all().select_related('course').prefetch_related('questions', 'attempts')
    
    # Calculate statistics
    active_quizzes = quizzes.filter(due_date__gte=timezone.now()).count()
    total_attempts = sum(quiz.attempts.count() for quiz in quizzes)
    avg_attempts = total_attempts // len(quizzes) if quizzes else 0
    
    # Calculate pending reminders
    pending_reminders = 0
    for quiz in quizzes.filter(due_date__gte=timezone.now()):
        enrolled_students = StudentCourse.objects.filter(course=quiz.course).count()
        attempted_students = quiz.attempts.values('student').distinct().count()
        pending_reminders += enrolled_students - attempted_students
    
    context = {
        'quizzes': quizzes,
        'active_quizzes': active_quizzes,
        'avg_attempts': avg_attempts,
        'pending_reminders': max(pending_reminders, 0),
    }
    return render(request, 'admin_quizzes.html', context)

@login_required
@user_passes_test(is_admin)
def admin_create_quiz(request):
    """Create a new quiz"""
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')
    
    # Get all courses - make sure this query works
    courses = Course.objects.all()
    
    # Add current date and time for the template header
    current_time = timezone.now()
    
    if request.method == 'POST':
        try:
            # Create quiz
            course = get_object_or_404(Course, id=request.POST.get('course'))
            quiz = Quiz.objects.create(
                course=course,
                title=request.POST.get('title'),
                description=request.POST.get('description', ''),
                due_date=request.POST.get('due_date'),
                time_limit=int(request.POST.get('time_limit', 30)),
                passing_score=int(request.POST.get('passing_score', 70))
            )
            
            # Create questions from the form data
            question_count = 0
            for key, value in request.POST.items():
                if key.startswith('question_text_'):
                    question_num = key.split('_')[-1]
                    question_text = value
                    option_a = request.POST.get(f'option_a_{question_num}')
                    option_b = request.POST.get(f'option_b_{question_num}')
                    option_c = request.POST.get(f'option_c_{question_num}', '')
                    option_d = request.POST.get(f'option_d_{question_num}', '')
                    correct_answer = request.POST.get(f'correct_answer_{question_num}')
                    
                    if question_text and option_a and option_b and correct_answer:
                        question = Question.objects.create(
                            quiz=quiz,
                            text=question_text,
                            order=question_count + 1
                        )
                        
                        # Create choices
                        Choice.objects.create(question=question, choice_text=option_a, is_correct=(correct_answer == 'A'))
                        Choice.objects.create(question=question, choice_text=option_b, is_correct=(correct_answer == 'B'))
                        if option_c:
                            Choice.objects.create(question=question, choice_text=option_c, is_correct=(correct_answer == 'C'))
                        if option_d:
                            Choice.objects.create(question=question, choice_text=option_d, is_correct=(correct_answer == 'D'))
                        
                        question_count += 1
            
            messages.success(request, f'Quiz "{quiz.title}" created successfully with {question_count} questions!')
            return redirect('admin_quizzes')
            
        except Exception as e:
            messages.error(request, f'Error creating quiz: {str(e)}')
    
    context = {
        'courses': courses,
        'current_date': current_time.strftime('%B %d, %Y'),
        'current_time': current_time.strftime('%I:%M %p')
    }
    return render(request, 'admin_create_quiz.html', context)
         
@login_required
@user_passes_test(is_admin)
def admin_quiz_reminders(request):
    """Manage and send quiz reminders"""
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')
    
    quizzes = Quiz.objects.filter(due_date__gte=timezone.now()).select_related('course')
    selected_quiz_id = request.GET.get('quiz_id')
    
    if request.method == 'POST':
        quiz_id = request.POST.get('quiz')
        reminder_type = request.POST.get('reminder_type', 'pending')
        custom_message = request.POST.get('message', '')
        
        try:
            quiz = get_object_or_404(Quiz, id=quiz_id)
            
            # Get enrolled students
            enrolled_students = BaseUser.objects.filter(user_type='student',
                studentcourse__course=quiz.course
            ).distinct()
            attempted_students = QuizAttempt.objects.filter(quiz=quiz).values_list('student', flat=True)
            
            if reminder_type == 'pending':
                students_to_notify = enrolled_students.exclude(id__in=attempted_students)
            elif reminder_type == 'all':
                students_to_notify = enrolled_students
            else:
                students_to_notify = enrolled_students.exclude(id__in=attempted_students)
            
            students_notified = 0
            for student in students_to_notify:
                # Calculate course progress for personalized message
                try:
                    student_course = StudentCourse.objects.get(student=student, course=quiz.course)
                    progress, watched_videos, total_videos = calculate_course_progress(student_course)
                except StudentCourse.DoesNotExist:
                    progress = 0
                
                # Send AI-powered reminder
                success = send_ai_quiz_reminder(student, quiz, progress, custom_message)
                if success:
                    students_notified += 1
            
            # Create reminder record
            QuizReminder.objects.create(
                quiz=quiz,
                students_count=students_notified,
                reminder_type=reminder_type
            )
            
            messages.success(request, f"Quiz reminders sent to {students_notified} students!")
            
        except Exception as e:
            messages.error(request, f'Error sending reminders: {str(e)}')
    
    # Calculate statistics
    pending_reminders = 0
    for quiz in quizzes:
        enrolled_students = StudentCourse.objects.filter(course=quiz.course).count()
        attempted_students = quiz.attempts.values('student').distinct().count()
        pending_reminders += enrolled_students - attempted_students
    
    # Get recent reminders
    recent_reminders = QuizReminder.objects.all().order_by('-sent_at')[:10]
    
    context = {
        'quizzes': quizzes,
        'pending_reminders': max(pending_reminders, 0),
        'sent_today': QuizReminder.objects.filter(sent_at__date=timezone.now().date()).count(),
        'students_notified': sum(reminder.students_count for reminder in recent_reminders),
        'recent_reminders': recent_reminders,
        'selected_quiz': selected_quiz_id
    }
    return render(request, 'admin_quiz_reminders.html', context)



# ============================================================================
# Student Quiz Views
# ============================================================================
@login_required
@user_passes_test(is_admin)
def admin_quiz_results(request):
    """View quiz results and analytics"""
    if not request.user.user_type == 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('admin_login')
    
    quizzes = Quiz.objects.all().select_related('course').prefetch_related('attempts')
    
    # Calculate quiz statistics
    quiz_stats = []
    total_attempts_sum = 0
    pending_students_sum = 0
    pass_rates = []
    
    for quiz in quizzes:
        attempts = quiz.attempts.all()
        total_attempts = attempts.count()
        total_attempts_sum += total_attempts
        
        if total_attempts > 0:
            avg_score = sum(attempt.score for attempt in attempts if attempt.score is not None) / total_attempts
            passing_attempts = attempts.filter(score__gte=quiz.passing_score).count()
            pass_rate = (passing_attempts / total_attempts) * 100
            pass_rates.append(pass_rate)
        else:
            avg_score = 0
            pass_rate = 0
        
        # Calculate pending students
        enrolled_students_count = StudentCourse.objects.filter(course=quiz.course).count()
        pending_students = enrolled_students_count - total_attempts
        pending_students_sum += pending_students
        
        quiz_stats.append({
            'quiz': quiz,
            'total_attempts': total_attempts,
            'avg_score': round(avg_score, 1),
            'pass_rate': round(pass_rate, 1),
            'pending_students': pending_students
        })
    
    # Calculate average pass rate
    avg_pass_rate = round(sum(pass_rates) / len(pass_rates), 1) if pass_rates else 0
    
    context = {
        'quiz_stats': quiz_stats,
        'total_attempts_sum': total_attempts_sum,
        'pending_students_sum': pending_students_sum,
        'avg_pass_rate': avg_pass_rate,
        'total_quizzes': quizzes.count(),
    }
    return render(request, 'admin_quiz_results.html', context)


# In views.py - Add this comprehensive student_quizzes view
@login_required
def student_quizzes(request):
    """Student view of all available quizzes with proper datetime handling"""
    student = request.user
    
    try:
        # Get enrolled courses
        enrolled_courses = StudentCourse.objects.filter(student=student).values_list('course_id', flat=True)
        
        # Get all quizzes for enrolled courses
        all_quizzes = Quiz.objects.filter(
            course_id__in=enrolled_courses
        ).select_related('course').prefetch_related('questions', 'attempts').order_by('due_date')
        
        # Organize quizzes by status
        pending_quizzes = []
        recent_attempts_list = []
        
        # Use timezone.now() for both datetime comparisons
        now = timezone.now()
        
        for quiz in all_quizzes:
            try:
                attempt = QuizAttempt.objects.filter(student=student, quiz=quiz).first()
                
                # Calculate days remaining - handle datetime properly
                if quiz.due_date:
                    # Both are datetime objects now
                    time_remaining = quiz.due_date - now
                    days_remaining = time_remaining.days
                else:
                    days_remaining = 0
                
                if attempt and attempt.is_completed:
                    # Add to recent attempts
                    recent_attempts_list.append(attempt)
                else:
                    # Add to pending quizzes (only if not expired)
                    if not quiz.due_date or quiz.due_date >= now:
                        quiz.days_remaining = days_remaining
                        pending_quizzes.append(quiz)
                        
            except Exception as e:
                print(f"Error processing quiz {quiz.id}: {str(e)}")
                continue
        
        # Calculate statistics
        total_quizzes = all_quizzes.count()
        total_pending_quizzes = len(pending_quizzes)
        completed_quizzes = len(recent_attempts_list)
        
        # Calculate average score with error handling
        total_score = 0
        valid_attempts = 0
        for attempt in recent_attempts_list:
            if attempt.score is not None:
                total_score += attempt.score
                valid_attempts += 1
        
        average_score = total_score / valid_attempts if valid_attempts > 0 else 0
        
        # Sort recent attempts by completion date (newest first)
        recent_attempts_list = sorted(
            recent_attempts_list, 
            key=lambda x: x.completed_at if x.completed_at else x.started_at, 
            reverse=True
        )[:5]
        
        context = {
            'pending_quizzes': pending_quizzes,
            'recent_attempts': recent_attempts_list,
            'total_quizzes': total_quizzes,
            'total_pending_quizzes': total_pending_quizzes,
            'completed_quizzes': completed_quizzes,
            'average_score': average_score,
        }
        
        return render(request, 'student_quizzes.html', context)
        
    except Exception as e:
        print(f"Error in student_quizzes view: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty context if there's an error
        context = {
            'pending_quizzes': [],
            'recent_attempts': [],
            'total_quizzes': 0,
            'total_pending_quizzes': 0,
            'completed_quizzes': 0,
            'average_score': 0,
        }
        return render(request, 'student_quizzes.html', context)
# In views.py - Update the take_quiz view

@login_required
def take_quiz(request, quiz_id):
    """Student takes a quiz and stores individual answers"""
    try:
        student = request.user
        quiz = get_object_or_404(
            Quiz.objects.select_related('course').prefetch_related(
                'questions__choices'
            ), 
            id=quiz_id
        )
        
        # Check if student is enrolled in the course
        if not StudentCourse.objects.filter(student=student, course=quiz.course).exists():
            messages.error(request, "You are not enrolled in this course.")
            return redirect('student_quizzes')
        
        # Check if quiz is still available
        if quiz.due_date and timezone.now() > quiz.due_date:
            messages.error(request, "This quiz has expired.")
            return redirect('student_quizzes')
        
        # Check if this is a retake
        previous_attempts = QuizAttempt.objects.filter(student=student, quiz=quiz).count()
        is_retake = previous_attempts > 0

        if request.method == 'POST':
            print(f"=== QUIZ SUBMISSION DEBUG ===")
            print(f"DEBUG: Starting quiz submission for {student.username}")
            
            # Get ALL POST data for debugging
            print("DEBUG: All POST data:", dict(request.POST))
            
            # Get JavaScript timing data
            actual_time_spent = request.POST.get('actual_time_spent')
            quiz_start_time = request.POST.get('quiz_start_time')
            
            print(f"DEBUG: JavaScript time spent: {actual_time_spent}")
            print(f"DEBUG: JavaScript start time: {quiz_start_time}")
            
            # FIXED: Use JavaScript timing if available
            if actual_time_spent and actual_time_spent.isdigit():
                time_taken_seconds = max(1, int(actual_time_spent))
                print(f"DEBUG: Using JavaScript timing: {time_taken_seconds} seconds")
            else:
                # If no JavaScript time, estimate based on question count
                time_taken_seconds = max(30, quiz.questions.count() * 30)
                print(f"DEBUG: Using estimated timing: {time_taken_seconds} seconds")
            
            # Create quiz attempt with PROPER timing
            start_time = timezone.now() - timedelta(seconds=time_taken_seconds)
            attempt = QuizAttempt.objects.create(
                student=student,
                quiz=quiz,
                started_at=start_time,
                is_completed=False
            )
            
            print(f"DEBUG: Created attempt ID: {attempt.id}")
            print(f"DEBUG: Start time set to: {start_time}")
            print(f"DEBUG: Current time: {timezone.now()}")
            
            # Process each question
            score = 0
            total_questions = quiz.questions.count()
            answered_questions = 0
            
            for question in quiz.questions.all():
                selected_choice_id = request.POST.get(f'question_{question.id}')
                
                if selected_choice_id and selected_choice_id != '':
                    try:
                        selected_choice = Choice.objects.get(id=selected_choice_id)
                        is_correct = selected_choice.is_correct
                        
                        if is_correct:
                            score += 1
                        
                        # Store student's answer
                        StudentAnswer.objects.create(
                            attempt=attempt,
                            question=question,
                            selected_choice=selected_choice,
                            is_correct=is_correct
                        )
                        answered_questions += 1
                        
                    except Choice.DoesNotExist:
                        StudentAnswer.objects.create(
                            attempt=attempt,
                            question=question,
                            selected_choice=None,
                            is_correct=False
                        )
                    except Exception as e:
                        StudentAnswer.objects.create(
                            attempt=attempt,
                            question=question,
                            selected_choice=None,
                            is_correct=False
                        )
                else:
                    StudentAnswer.objects.create(
                        attempt=attempt,
                        question=question,
                        selected_choice=None,
                        is_correct=False
                    )
            
            # Calculate percentage
            percentage = (score / total_questions) * 100 if total_questions > 0 else 0
            
            print(f"DEBUG: Final score - {score}/{total_questions} = {percentage}%")
            
            # FIXED: Update attempt with COMPLETION time and stored time
            attempt.score = percentage
            attempt.is_completed = True
            attempt.completed_at = timezone.now()
            attempt.time_taken = time_taken_seconds  # Store the actual seconds
            attempt.is_retake = is_retake
            
            attempt.save()
            
            print(f"DEBUG: Saved attempt details:")
            print(f"DEBUG: - Score: {attempt.score}%")
            print(f"DEBUG: - Time taken: {attempt.time_taken} seconds")
            print(f"DEBUG: - Started at: {attempt.started_at}")
            print(f"DEBUG: - Completed at: {attempt.completed_at}")
            print("=== END DEBUG ===")
            
            if is_retake:
                message = f"Quiz retaken! Your new score: {percentage:.1f}% - {'Passed' if percentage >= quiz.passing_score else 'Failed'}"
            else:
                message = f"Quiz completed! Your score: {percentage:.1f}% - {'Passed' if percentage >= quiz.passing_score else 'Failed'}"
            
            messages.success(request, message)
            return redirect('quiz_result', quiz_id=quiz.id)
        
        # GET request - show quiz form
        questions = quiz.questions.all().prefetch_related('choices').order_by('order')
        
        # Get previous score for retake context
        previous_score = None
        if is_retake:
            last_attempt = QuizAttempt.objects.filter(
                student=student, 
                quiz=quiz
            ).order_by('-completed_at').first()
            previous_score = last_attempt.score if last_attempt else None
        
        context = {
            'quiz': quiz,
            'questions': questions,
            'time_limit_minutes': quiz.time_limit,
            'is_retake': is_retake,
            'previous_score': previous_score,
            'attempt_count': previous_attempts + 1,
            'total_questions': questions.count(),
        }
        return render(request, 'take_quiz.html', context)
        
    except Exception as e:
        print(f"ERROR in take_quiz view: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Error loading quiz: {str(e)}")
        return redirect('student_quizzes')


# In views.py - Update the quiz_result view
@login_required
def quiz_result(request, quiz_id):
    """View detailed quiz results with individual answer tracking"""
    try:
        student = request.user
        quiz = get_object_or_404(Quiz, id=quiz_id)
        
        # Get the latest quiz attempt with all related data
        attempt = QuizAttempt.objects.filter(
            student=student, 
            quiz=quiz,
            is_completed=True
        ).select_related('quiz', 'quiz__course').prefetch_related(
            'student_answers__question',
            'student_answers__selected_choice',
            'student_answers__question__choices'
        ).order_by('-completed_at').first()
        
        if not attempt:
            messages.error(request, "No quiz attempt found.")
            return redirect('student_quizzes')
        
        # Calculate statistics from stored answers
        total_questions = quiz.questions.count()
        student_answers = attempt.student_answers.all()
        
        # Calculate metrics properly
        correct_answers = student_answers.filter(is_correct=True).count()
        incorrect_answers = student_answers.filter(is_correct=False, selected_choice__isnull=False).count()
        unanswered_questions = student_answers.filter(selected_choice__isnull=True).count()
        
        # Use the stored score
        score_percentage = attempt.score if attempt.score is not None else 0
        
        # FIXED: Calculate time taken properly
        time_taken_str = "Not recorded"
        time_taken_seconds = 0
        
        if attempt.started_at and attempt.completed_at:
            # Calculate time difference
            time_difference = attempt.completed_at - attempt.started_at
            time_taken_seconds = int(time_difference.total_seconds())
            
            # Format time as "X minutes Y seconds"
            minutes = time_taken_seconds // 60
            seconds = time_taken_seconds % 60
            
            if minutes > 0 and seconds > 0:
                time_taken_str = f"{minutes} minutes {seconds} seconds"
            elif minutes > 0:
                time_taken_str = f"{minutes} minutes"
            else:
                time_taken_str = f"{seconds} seconds"
        
        # Calculate points (1 point per correct answer)
        points_earned = correct_answers
        total_points = total_questions
        
        # Prepare detailed question reviews
        question_reviews = []
        
        for question in quiz.questions.all().prefetch_related('choices'):
            # Find student's answer for this question
            student_answer = student_answers.filter(question=question).first()
            
            # Find correct choice
            correct_choice = question.choices.filter(is_correct=True).first()
            
            if student_answer and student_answer.selected_choice:
                user_answer_text = student_answer.selected_choice.choice_text
                is_correct = student_answer.is_correct
                answer_status = "answered"
            else:
                user_answer_text = "Not answered"
                is_correct = False
                answer_status = "unanswered"
            
            correct_answer_text = correct_choice.choice_text if correct_choice else "No correct answer defined"
            
            question_reviews.append({
                'question_text': question.text,
                'user_answer': user_answer_text,
                'correct_answer': correct_answer_text,
                'is_correct': is_correct,
                'answer_status': answer_status,
                'explanation': getattr(question, 'explanation', 'No explanation available.')
            })
        
        context = {
            'quiz': quiz,
            'score_percentage': score_percentage,
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'incorrect_answers': incorrect_answers,
            'unanswered_questions': unanswered_questions,
            'time_taken': time_taken_str,  # This will now show "X minutes Y seconds"
            'time_taken_seconds': time_taken_seconds,
            'completion_date': attempt.completed_at if attempt.completed_at else timezone.now(),
            'points_earned': points_earned,
            'total_points': total_points,
            'question_reviews': question_reviews,
            'attempt': attempt,
            'is_retake': attempt.is_retake,
            'actual_passed': score_percentage >= quiz.passing_score,
        }
        
        return render(request, 'quiz_result.html', context)
        
    except Exception as e:
        print(f"ERROR in quiz_result view: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Error loading quiz results: {str(e)}")
        return redirect('student_quizzes')
# Add these functions to your views.py file, preferably after the student_dashboard function

@login_required
@csrf_exempt
@require_POST
def dismiss_alert(request, alert_id):
    """Dismiss a dashboard alert"""
    try:
        from .models import DashboardAlert
        alert = get_object_or_404(DashboardAlert, id=alert_id, student=request.user)
        alert.is_active = False
        alert.dismissed_at = timezone.now()
        alert.save()
        
        return JsonResponse({'success': True, 'message': 'Alert dismissed'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_alerts_count(request):
    """Get count of active alerts for badge display"""
    from .models import DashboardAlert
    active_count = DashboardAlert.objects.filter(
        student=request.user, 
        is_active=True
    ).count()
    
    return JsonResponse({'active_count': active_count})

# Also add this function to update the student_dashboard view with quiz data
def update_student_dashboard_with_quizzes(request):
    """Helper function to add quiz data to dashboard context"""
    student = request.user
    
    # Get enrolled courses
    enrolled_courses = StudentCourse.objects.filter(student=student).values_list('course_id', flat=True)
    
    # Get pending quizzes
    pending_quizzes = Quiz.objects.filter(
        course_id__in=enrolled_courses,
        due_date__gte=timezone.now()
    ).exclude(
        attempts__student=student
    ).select_related('course').order_by('due_date')[:5]
    
    # Get recent quiz attempts
    recent_attempts = QuizAttempt.objects.filter(
        student=student
    ).select_related('quiz', 'quiz__course').order_by('-completed_at')[:5]
    
    # Count total pending quizzes
    total_pending_quizzes = Quiz.objects.filter(
        course_id__in=enrolled_courses,
        due_date__gte=timezone.now()
    ).exclude(
        attempts__student=student
    ).count()
    
    # Count completed quizzes
    completed_quizzes = QuizAttempt.objects.filter(student=student).count()
    
    return {
        'pending_quizzes': pending_quizzes,
        'recent_attempts': recent_attempts,
        'total_pending_quizzes': total_pending_quizzes,
        'completed_quizzes': completed_quizzes,
    }


@login_required
def submit_quiz(request, quiz_id):
    """Handle quiz submission"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    student = request.user
    
    if request.method == 'POST':
        try:
            # Calculate score
            total_questions = quiz.questions.count()
            correct_answers = 0
            
            for question in quiz.questions.all():
                selected_choice_id = request.POST.get(f'question_{question.id}')
                if selected_choice_id:
                    selected_choice = Choice.objects.get(id=selected_choice_id)
                    if selected_choice.is_correct:
                        correct_answers += 1
            
            # Calculate percentage
            score_percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
            
            # Create or update quiz attempt
            attempt, created = QuizAttempt.objects.get_or_create(
                student=student,
                quiz=quiz,
                defaults={
                    'score': score_percentage,
                    'is_completed': True,
                    'completed_at': timezone.now()
                }
            )
            
            if not created:
                attempt.score = score_percentage
                attempt.is_completed = True
                attempt.completed_at = timezone.now()
                attempt.save()
            
            messages.success(request, f'Quiz submitted successfully! Score: {score_percentage:.1f}%')
            return redirect('quiz_result', quiz_id=quiz.id)
            
        except Exception as e:
            messages.error(request, f'Error submitting quiz: {str(e)}')
            return redirect('take_quiz', quiz_id=quiz.id)
    
    return redirect('student_quizzes')