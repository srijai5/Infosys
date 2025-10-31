# admin.py
from django.contrib import admin
from .models import NotificationPreference, EmailLog, DashboardAlert, Quiz, Question, Choice, QuizAttempt

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['student', 'email_notifications', 'dashboard_alerts', 'reminder_frequency']
    list_filter = ['email_notifications', 'dashboard_alerts', 'reminder_frequency']

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['student', 'email_type', 'subject', 'sent_at', 'success']
    list_filter = ['email_type', 'success', 'sent_at']
    search_fields = ['student__username', 'subject']

@admin.register(DashboardAlert)
class DashboardAlertAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'alert_type', 'is_active', 'created_at']
    list_filter = ['alert_type', 'is_active', 'created_at']
    search_fields = ['student__username', 'course__course_name']

# QUIZ ADMIN INTERFACES - UPDATED TO MATCH YOUR MODELS
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4
    fields = ['text', 'is_correct', 'order']

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ['text', 'order']

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'question_count', 'due_date', 'created_at']
    list_filter = ['course', 'due_date', 'created_at']
    search_fields = ['title', 'course__course_name', 'description']
    inlines = [QuestionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'course')
        }),
        ('Settings', {
            'fields': ('due_date', 'time_limit', 'passing_score')
        }),
    )
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text_short', 'quiz', 'order', 'created_at']
    list_filter = ['quiz', 'created_at']
    search_fields = ['text', 'quiz__title']
    inlines = [ChoiceInline]
    
    def text_short(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_short.short_description = 'Question'

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['text_short', 'question', 'is_correct', 'order']
    list_filter = ['question__quiz', 'is_correct']
    search_fields = ['text', 'question__text']
    
    def text_short(self, obj):
        return obj.text[:30] + '...' if len(obj.text) > 30 else obj.text
    text_short.short_description = 'Choice'

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'quiz', 'score', 'passed_display', 'completed_at']
    list_filter = ['quiz', 'completed_at']  # Removed 'passed' from list_filter
    search_fields = ['student__username', 'quiz__title']
    readonly_fields = ['completed_at']
    
    def passed_display(self, obj):
        return obj.passed if obj.score else False
    passed_display.boolean = True
    passed_display.short_description = 'Passed'