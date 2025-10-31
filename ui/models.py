from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

# Base User Model (replaces ui_student)
class BaseUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('admin', 'Administrator'),
    )
    
    user_type = models.CharField(
        max_length=20, 
        choices=USER_TYPE_CHOICES, 
        default='student'
    )
    date_of_birth = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'ui_baseuser'  # Explicit table name
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.username} ({self.user_type})"

    @property
    def is_student(self):
        return self.user_type == 'student'
    
    @property
    def is_administrator(self):
        return self.user_type == 'admin'

# Student Profile
class StudentProfile(models.Model):
    user = models.OneToOneField(
        BaseUser, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='student_profile'
    )
    student_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    enrollment_date = models.DateField(auto_now_add=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    parent_phone = models.CharField(max_length=15, blank=True, null=True)
    emergency_contact = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'ui_studentprofile'

    def __str__(self):
        return f"Student: {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = f"STU{self.user.id:06d}"
        super().save(*args, **kwargs)

# Admin Profile
class AdminProfile(models.Model):
    user = models.OneToOneField(
        BaseUser, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='admin_profile'
    )
    admin_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    role = models.CharField(max_length=100, default='Administrator')
    department = models.CharField(max_length=100, blank=True, null=True)
    can_manage_users = models.BooleanField(default=True)
    can_manage_courses = models.BooleanField(default=True)
    can_manage_content = models.BooleanField(default=True)

    class Meta:
        db_table = 'ui_adminprofile'

    def __str__(self):
        return f"Admin: {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.admin_id:
            self.admin_id = f"ADM{self.user.id:06d}"
        super().save(*args, **kwargs)

# Signal to create profiles automatically
@receiver(post_save, sender=BaseUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == 'student':
            StudentProfile.objects.create(user=instance)
        elif instance.user_type == 'admin':
            AdminProfile.objects.create(user=instance)

# Keep your existing models but update foreign keys to use BaseUser
class Course(models.Model):
    course_name = models.CharField(max_length=200)
    description = models.TextField()
    duration_weeks = models.IntegerField()
    image = models.ImageField(upload_to='course_images/', null=True, blank=True)
    #created_by = models.ForeignKey(
     #   BaseUser, 
      #  on_delete=models.SET_NULL, 
       # null=True, 
        #limit_choices_to={'user_type': 'admin'},
        #related_name='created_courses'
    #a)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'ui_course'

    def __str__(self):
        return self.course_name

class Video(models.Model):
    course = models.ForeignKey(Course, related_name='videos', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    youtube_url = models.URLField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'ui_video'
        ordering = ['order']

    def __str__(self):
        return f"{self.course.course_name} - {self.title}"

class StudentCourse(models.Model):
    student = models.ForeignKey(
        BaseUser, 
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'student'}
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    target_completion_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paused', 'Paused')
    ], default='not_started')
    priority = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='medium')
    notes = models.TextField(blank=True, null=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ui_studentcourse'
        unique_together = ['student', 'course']

    def __str__(self):
        return f"{self.student.username} - {self.course.course_name}"

# Add your other models here with updated foreign keys...
    # ========== COURSE PROGRESS PROPERTIES ==========
    
    @property
    def needs_reminder(self):
        """Check if course needs reminder (incomplete but started)"""
        return 0 < self.course_progress < 100
    
    @property
    def high_completion_alert(self):
        """Check if course qualifies for high completion alert (75%+)"""
        return 75 <= self.course_progress < 100
    
    @property
    def has_pending_quiz(self):
        """Check if this course has any pending quizzes"""
        return self.course.contents.filter(content_type='quiz').exists()
    
    def get_reminder_context(self):
        """Get context data for reminder emails/alerts"""
        return {
            'student_name': self.student.get_full_name() or self.student.username,
            'course_name': self.course.course_name,
            'progress_percentage': self.course_progress,
            'watched_videos': self.watched_videos_count,
            'total_videos': self.total_videos_count,
            'has_pending_quiz': self.has_pending_quiz,
            'needs_high_completion_alert': self.high_completion_alert
        }
    
    @property
    def course_progress(self):
        """Calculate progress for this specific course"""
        total_videos = self.course.videos.count()
        if total_videos == 0:
            return 0
        
        watched_videos = self.video_progress.filter(watched=True).count()
        return round((watched_videos / total_videos) * 100)
    
    @property
    def watched_videos_count(self):
        return self.video_progress.filter(watched=True).count()
    
    @property
    def total_videos_count(self):
        return self.course.videos.count()
    
    def mark_completed(self):
        """Mark course as completed"""
        self.status = 'completed'
        self.completed = True
        self.completed_at = timezone.now()
        self.save()

# ----------------------------
class StudentVideoProgress(models.Model):
    student_course = models.ForeignKey(StudentCourse, on_delete=models.CASCADE, related_name='video_progress')
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    watched = models.BooleanField(default=False)
    watched_at = models.DateTimeField(null=True, blank=True)
    last_watched_time = models.FloatField(default=0.0)  # in seconds

    class Meta:
        unique_together = ('student_course', 'video')

    def mark_watched(self):
        self.watched = True
        self.watched_at = timezone.now()
        self.save()

# ----------------------------
# Course Content (Documents/Quizzes)
# ----------------------------
class CourseContent(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='contents')
    title = models.CharField(max_length=200)
    content_type = models.CharField(
        max_length=50,
        choices=[('video', 'Video'), ('document', 'Document'), ('quiz', 'Quiz')],
        default='video'
    )
    file = models.FileField(upload_to='course_contents/')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.course_name} - {self.title}"

# ----------------------------
# Activity & Study Session
# ----------------------------
class Activity(models.Model):
    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.description}"

# ----------------------------
# Quiz & Results
# ----------------------------
# ----------------------------
# Enhanced Quiz System
# ----------------------------
# Add to your existing models.py - ENHANCED QUIZ SYSTEM

class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField()  # Add this field
    time_limit = models.IntegerField(default=30, help_text="Time limit in minutes")
    passing_score = models.IntegerField(default=70, help_text="Passing percentage")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_quiz'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.course.course_name}"

    @property
    def is_available(self):
        """Check if quiz is still active (before due date)"""
        return timezone.now() <= self.due_date

    @property
    def total_questions(self):
        return self.questions.count()

    # 🚀 ADD THIS METHOD FOR AUTOMATIC REMINDERS
    def send_automatic_quiz_creation_reminders(self):
        """AUTOMATIC: Send reminders to all enrolled students when quiz is created"""
        try:
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            from ui.services import get_time_greeting, get_quiz_motivation
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Get all students enrolled in the course
            enrolled_students = BaseUser.objects.filter(
                user_type='student',
                studentcourse__course=self.course
            ).distinct()
            
            reminders_sent = 0
            
            for student in enrolled_students:
                try:
                    # Get student's course progress
                    student_course = StudentCourse.objects.get(
                        student=student,
                        course=self.course
                    )
                    course_progress = student_course.course_progress
                    
                    # Prepare email content
                    time_greeting = get_time_greeting()
                    quiz_motivation = get_quiz_motivation(course_progress)
                    
                    context = {
                        'time_greeting': time_greeting,
                        'quiz_motivation': quiz_motivation,
                        'student_name': student.first_name or student.username,
                        'quiz_title': self.title,
                        'course_name': self.course.course_name,
                        'course_progress': course_progress,
                        'due_date': self.due_date.strftime("%B %d, %Y at %I:%M %p") if self.due_date else "No due date",
                        'quiz_url': f"/student/quiz/{self.id}/take/",
                        'custom_message': "🎯 New quiz available! Check it out now."
                    }
                    
                    # Render email template
                    email_html = render_to_string('ai_quiz_reminder_email.html', context)
                    plain_message = strip_tags(email_html)
                    
                    # SEND ACTUAL EMAIL AUTOMATICALLY
                    send_mail(
                        subject=f"📝 New Quiz: {self.title}",
                        message=plain_message,
                        from_email='studytrack.platform@gmail.com',
                        recipient_list=[student.email],
                        html_message=email_html,
                        fail_silently=False,
                    )
                    
                    # Create reminder record
                    QuizReminder.objects.create(
                        quiz=self,
                        student=student,
                        reminder_type='automatic_creation'
                    )
                    
                    reminders_sent += 1
                    logger.info(f"✅ AUTOMATIC: Quiz creation reminder sent to {student.email}")
                    
                except StudentCourse.DoesNotExist:
                    continue
                except Exception as e:
                    logger.error(f"❌ Error sending auto-reminder to {student.email}: {str(e)}")
                    continue
            
            logger.info(f"✅ AUTOMATIC: Sent {reminders_sent} quiz creation reminders for '{self.title}'")
            return reminders_sent
            
        except Exception as e:
            logger.error(f"❌ Error in automatic quiz creation reminders: {str(e)}")
            return 0

    # 🚀 ADD THIS SAVE METHOD TO TRIGGER AUTOMATIC REMINDERS
    
    # ... your existing fields ...
    
    def save(self, *args, **kwargs):
        """Override save to send automatic reminders when quiz is created"""
        is_new = self.pk is None  # Check if this is a new quiz
        super().save(*args, **kwargs)
        
        # AUTOMATIC: Send reminders when new quiz is created
        if is_new:
            try:
                from ui.tasks import send_quiz_creation_reminders_task
                send_quiz_creation_reminders_task.delay(self.id)
                print(f"🚀 AUTOMATIC: Triggered quiz creation reminders for '{self.title}'")
            except Exception as e:
                print(f"❌ Error triggering automatic reminders: {str(e)}")
    

class Question(models.Model):
    """Question model for quizzes"""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()  # Change from question_text to text
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ui_question'
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.text[:50]}..."
    
    
class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'ui_choice'
        ordering = ['order']

    def __str__(self):
        return f"{self.choice_text} ({'✓' if self.is_correct else '✗'})"

class QuizAttempt(models.Model):
    student = models.ForeignKey(
        BaseUser, 
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'student'},
        related_name='quiz_attempts'
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    time_taken = models.IntegerField(default=0, help_text="Time taken in minutes")
    is_retake = models.BooleanField(default=False)  # Add this field to track retakes

    class Meta:
        db_table = 'ui_quizattempt'
        # REMOVE unique_together to allow multiple attempts
        ordering = ['-started_at']

    def __str__(self):
        status = "Completed" if self.is_completed else "In Progress"
        retake_info = " (Retake)" if self.is_retake else ""
        return f"{self.student.username} - {self.quiz.title} ({status}{retake_info})"

    @property
    def passed(self):
        return self.score >= self.quiz.passing_score if self.score else False

    def save(self, *args, **kwargs):
        # Auto-calculate time_taken if both dates are available
        if self.completed_at and self.started_at:
            time_difference = self.completed_at - self.started_at
            self.time_taken = int(time_difference.total_seconds() / 60)  # Convert to minutes
        
        # Auto-detect if this is a retake
        if not self.is_retake and self.pk is None:  # Only for new instances
            previous_attempts = QuizAttempt.objects.filter(
                student=self.student, 
                quiz=self.quiz
            ).count()
            if previous_attempts > 0:
                self.is_retake = True
        
        super().save(*args, **kwargs)


# Add this after your existing QuizAttempt model in models.py

class QuizReminder(models.Model):
    """Track quiz reminders sent to students"""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='reminders')
    student = models.ForeignKey(
        BaseUser, 
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'student'}
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    reminder_type = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Attempts'),
            ('all', 'All Students'),
            ('custom', 'Custom Selection')
        ],
        default='pending'
    )
    students_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'ui_quizreminder'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Reminder for {self.quiz.title} - {self.student.username}"
# Notification System Models
# ----------------------------



    # Add these to your existing models.py

class NotificationPreference(models.Model):
    """Store user preferences for notifications"""
    student = models.OneToOneField(
        BaseUser, 
        on_delete=models.CASCADE, 
        related_name='notification_preferences',
        limit_choices_to={'user_type': 'student'}
    )
    email_notifications = models.BooleanField(default=True)
    dashboard_alerts = models.BooleanField(default=True)
    reminder_frequency = models.CharField(
        max_length=20,
        choices=[
            ('disabled', 'Disabled'),
            ('daily', 'Daily'),
            ('multiple', 'Multiple Times Daily')
        ],
        default='multiple'
    )
    
    class Meta:
        db_table = 'ui_notificationpreference'

    def __str__(self):
        return f"Notification preferences for {self.student.username}"

class EmailLog(models.Model):
    """Track all emails sent to users"""
    student = models.ForeignKey(
        BaseUser, 
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'student'}
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    email_type = models.CharField(
        max_length=50,
        choices=[
            ('course_reminder', 'Course Reminder'),
            ('quiz_reminder', 'Quiz Reminder'),
            ('progress_alert', 'Progress Alert')
        ]
    )
    success = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'ui_emaillog'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.email_type} to {self.student.username}"

class DashboardAlert(models.Model):
    """Store active alerts for user dashboard"""
    student = models.ForeignKey(
        BaseUser, 
        on_delete=models.CASCADE, 
        related_name='alerts',
        limit_choices_to={'user_type': 'student'}
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    alert_type = models.CharField(
        max_length=50,
        choices=[
            ('high_completion', 'High Completion (75%+)'),
            ('quiz_pending', 'Quiz Pending'),
            ('course_reminder', 'Course Reminder')
        ]
    )
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'ui_dashboardalert'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.alert_type} - {self.course.course_name}"
    

# Add this to your models.py after the QuizAttempt model
class StudentAnswer(models.Model):
    """Track individual student answers for quiz questions"""
    attempt = models.ForeignKey(
        QuizAttempt, 
        on_delete=models.CASCADE, 
        related_name='student_answers'
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ui_studentanswer'
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        return f"{self.attempt.student.username} - {self.question.text[:50]}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate if the answer is correct
        if self.selected_choice:
            self.is_correct = self.selected_choice.is_correct
        super().save(*args, **kwargs)


# Add this to your models.py after the existing models
# Add to your models.py



    

# In your models.py, update the create_quiz_dashboard_alert method in the command
# Or better, create a separate fix in the management command:

# Add this to your management command file (send_quiz_reminders.py)
# Add to your existing models.py

class HighCompletionAlert(models.Model):
    """Track high course completion alerts (75%+)"""
    student = models.ForeignKey(
        BaseUser, 
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'student'},
        related_name='high_completion_alerts'
    )
    student_course = models.ForeignKey(StudentCourse, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    alert_type = models.CharField(
        max_length=50,
        choices=[
            ('high_completion', 'High Completion (75%+)'),
            ('almost_complete', 'Almost Complete (90%+)'),
            ('completion_urgent', 'Completion Urgent (95%+)')
        ],
        default='high_completion'
    )
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    is_dismissed = models.BooleanField(default=False)
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'), 
            ('high', 'High'),
            ('urgent', 'Urgent')
        ],
        default='medium'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'ui_highcompletionalert'
        ordering = ['-priority', '-created_at']
        unique_together = ['student', 'student_course', 'is_active']
    
    def __str__(self):
        return f"{self.student.username} - {self.course.course_name} ({self.alert_type})"
    
    def dismiss(self):
        """Dismiss the alert"""
        self.is_active = False
        self.is_dismissed = True
        self.dismissed_at = timezone.now()
        self.save()
    
    @classmethod
    def create_high_completion_alert(cls, student_course):
        """Create high completion alert for a student course"""
        progress = student_course.course_progress
        
        if 75 <= progress < 90:
            alert_type = 'high_completion'
            priority = 'medium'
        elif 90 <= progress < 95:
            alert_type = 'almost_complete' 
            priority = 'high'
        elif progress >= 95:
            alert_type = 'completion_urgent'
            priority = 'urgent'
        else:
            return None
        
        # Check if active alert already exists
        existing_alert = cls.objects.filter(
            student=student_course.student,
            student_course=student_course,
            is_active=True
        ).first()
        
        if existing_alert:
            # Update existing alert
            existing_alert.alert_type = alert_type
            existing_alert.priority = priority
            existing_alert.message = cls._generate_message(student_course, alert_type)
            existing_alert.save()
            return existing_alert
        
        # Create new alert
        alert = cls.objects.create(
            student=student_course.student,
            student_course=student_course,
            course=student_course.course,
            alert_type=alert_type,
            priority=priority,
            message=cls._generate_message(student_course, alert_type)
        )
        return alert
    
    @staticmethod
    def _generate_message(student_course, alert_type):
        """Generate alert message based on progress"""
        progress = student_course.course_progress
        course_name = student_course.course.course_name
        
        messages = {
            'high_completion': f"Great progress! You've completed {progress}% of '{course_name}'. You're almost there!",
            'almost_complete': f"Amazing! You're at {progress}% completion for '{course_name}'. Just a little more to go!",
            'completion_urgent': f"Almost done! You're at {progress}% completion for '{course_name}'. Finish strong!"
        }
        
        return messages.get(alert_type, f"You're making great progress in '{course_name}'!")

# Add this method to your StudentCourse model
def check_and_create_high_completion_alert(self):
    """Check if course qualifies for high completion alert and create one"""
    progress = self.course_progress
    
    if 75 <= progress < 100 and not self.completed:
        return HighCompletionAlert.create_high_completion_alert(self)
    return None

# Add this property to StudentCourse model if not already there
@property
def qualifies_high_completion_alert(self):
    """Check if course qualifies for high completion alert"""
    return 75 <= self.course_progress < 100 and not self.completed