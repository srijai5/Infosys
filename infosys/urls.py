# ui/urls.py
from django.urls import path
from django.shortcuts import redirect
from ui import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ----------------------------
    # Home
    # ----------------------------
    path('', views.home, name='index'),

    # ----------------------------
    # Student Authentication
    # ----------------------------
    path('student/register/', views.student_register, name='student_register'),
    path('student/login/', views.student_login, name='student_login'),
    path('student/logout/', views.student_logout, name='student_logout'),

    # ----------------------------
    # Student Dashboard
    # ----------------------------
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/dashboard/data/', views.student_dashboard_data, name='student_dashboard_data'),

    # ----------------------------
    # Student Settings
    # ----------------------------
    path('student/settings/', views.settings, name='settings'),

    # ----------------------------
    # Student Performance & Recommendations
    # ----------------------------
    path('student/performance/', views.performance, name='performance'),
    path('student/performance/data/', views.performance_data, name='performance_data'),
    path('student/recommendations/', views.recommendations, name='recommendations'),

    # ----------------------------
    # Student Courses
    # ----------------------------
    path('student/courses/', views.enroll_courses_list, name='enroll_courses'),
    path('student/courses/enroll/<int:course_id>/', views.enroll_course, name='enroll_course'),
    path('student/courses/complete/<int:student_course_id>/', views.complete_course, name='complete_course'),
    path('student/course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('student/my-courses/', views.my_courses, name='my_courses'),
    
    # ----------------------------
    # Video Progress Tracking
    # ----------------------------
    path(
        'student/course/<int:student_course_id>/video/<int:video_id>/watched/',
        views.mark_video_watched,
        name='mark_video_watched'
    ),
    path('student/update-video-progress/', views.update_video_progress, name='update_video_progress'),

    # ----------------------------
    # Admin Authentication
    # ----------------------------
    path('admin/register/', views.admin_signup, name='admin_signup'),
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/logout/', views.admin_logout, name='admin_logout'),

    # ----------------------------
    # Admin Dashboard
    # ----------------------------
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/dashboard/data/', views.admin_dashboard_data, name='admin_dashboard_data'),

    # ----------------------------
    # Admin Students Management
    # ----------------------------
    path('admin/students/', views.admin_students, name='admin_students'),
    
    # Student Detail API
    path('admin/student/<int:id>/', views.get_student_details, name='get_student_details'),
    
    # Student CRUD API Endpoints
    path('admin/students/add/', views.admin_add_student, name='admin_add_student'),
    path('admin/students/edit/', views.admin_edit_student, name='admin_edit_student'),
    path('admin/students/delete/', views.admin_delete_student, name='admin_delete_student'),

    # ----------------------------
    # Quiz Management URLs
    # ----------------------------
    path('admin/quizzes/', views.admin_quizzes, name='admin_quizzes'),
    path('admin/quizzes/create/', views.admin_create_quiz, name='admin_create_quiz'),
    path('admin/quizzes/<int:quiz_id>/', views.admin_view_quiz, name='admin_view_quiz'),
    path('admin/quizzes/<int:quiz_id>/edit/', views.admin_edit_quiz, name='admin_edit_quiz'), 
    path('admin/quizzes/<int:quiz_id>/delete/', views.admin_delete_quiz, name='admin_delete_quiz'),
    path('admin/quiz-reminders/', views.admin_quiz_reminders, name='admin_quiz_reminders'),
    path('admin/quiz-results/', views.admin_quiz_results, name='admin_quiz_results'),

    # ----------------------------
    # Student Quiz URLs
    # ----------------------------
    
    
    path('student/quizzes/', views.student_quizzes, name='student_quizzes'),
    path('student/quiz/<int:quiz_id>/take/', views.take_quiz, name='take_quiz'),
    path('quiz/<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('student/quiz/<int:quiz_id>/result/', views.quiz_result, name='quiz_result'),

    # ----------------------------
    # Admin Analytics
    # ----------------------------
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
    path('admin/analytics/data/', views.admin_analytics_data, name='admin_analytics_data'),

    # ----------------------------
    # Admin Settings
    # ----------------------------
    path('admin/settings/', views.admin_settings, name='admin_settings'),
    path('admin/profile-settings/', views.admin_profile_settings, name='admin_profile_settings'),

    # ----------------------------
    # Admin Courses
    # ----------------------------
    path('admin/courses/', views.admin_courses, name='admin_courses'),
    path('admin/courses/add/', views.add_course, name='add_course'),
    path('admin/courses/data/<int:course_id>/', views.course_data, name='course_data'),
    path('admin/courses/edit/<int:course_id>/', views.edit_course, name='edit_course'),
    path('admin/courses/delete/<int:course_id>/', views.delete_course, name='delete_course'),

    # ----------------------------
    # MILESTONE 3: Course Assignment System
    # ----------------------------
    path('admin/assign-courses/', views.assign_courses, name='assign_courses'),
    path('admin/assign-courses/save/', views.save_course_assignments, name='save_course_assignments'),
    path('admin/student-study-tracks/', views.student_study_tracks, name='student_study_tracks'),
    
    # Assignment Management APIs
    path('api/student-assignments/<int:student_id>/', views.get_student_assignments_api, name='get_student_assignments_api'),
    path('api/assignments/<int:assignment_id>/delete/', views.delete_assignment_api, name='delete_assignment_api'),
    path('api/assignments/<int:assignment_id>/update/', views.update_assignment_api, name='update_assignment_api'),

    # ----------------------------
    # Shortcut redirects
    # ----------------------------
    path('login/', lambda request: redirect('student_login'), name='login_redirect'),
    path('register/', lambda request: redirect('student_register'), name='register_redirect'),
    path('logout/', lambda request: redirect('student_logout'), name='logout_redirect'),
    path('dashboard/', lambda request: redirect('student_dashboard'), name='dashboard_redirect'),
]

# Serve media files in DEBUG mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)