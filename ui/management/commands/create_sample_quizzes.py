# management/commands/create_sample_quizzes.py
from django.core.management.base import BaseCommand
from ui.models import Quiz, Question, Choice, Course

class Command(BaseCommand):
    help = 'Create sample quizzes with questions and choices for Task 2'
    
    def handle(self, *args, **options):
        courses = Course.objects.all()
        
        quiz_data = [
            {
                "title": "HTML Basics Quiz",
                "description": "Test your understanding of HTML fundamentals",
                "course_filter": "Web Development",
                "questions": [
                    {
                        "text": "What does HTML stand for?",
                        "type": "multiple_choice",
                        "choices": [
                            {"text": "Hyper Text Markup Language", "correct": True},
                            {"text": "High Tech Modern Language", "correct": False},
                            {"text": "Hyper Transfer Markup Language", "correct": False},
                            {"text": "Home Tool Markup Language", "correct": False}
                        ]
                    },
                    {
                        "text": "Which tag is used for the largest heading?",
                        "type": "multiple_choice",
                        "choices": [
                            {"text": "<h1>", "correct": True},
                            {"text": "<head>", "correct": False},
                            {"text": "<h6>", "correct": False},
                            {"text": "<heading>", "correct": False}
                        ]
                    }
                ]
            },
            {
                "title": "CSS Fundamentals Test", 
                "description": "Evaluate your CSS knowledge and styling skills",
                "course_filter": "Web Development",
                "questions": [
                    {
                        "text": "Which property is used to change the background color?",
                        "type": "multiple_choice", 
                        "choices": [
                            {"text": "background-color", "correct": True},
                            {"text": "color", "correct": False},
                            {"text": "bgcolor", "correct": False},
                            {"text": "background", "correct": False}
                        ]
                    }
                ]
            }
        ]
        
        created_count = 0
        for data in quiz_data:
            course = courses.filter(course_name__icontains=data['course_filter']).first()
            if course:
                quiz, created = Quiz.objects.get_or_create(
                    title=data['title'],
                    course=course,
                    defaults={
                        'description': data['description'],
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f"✅ Created quiz: {quiz.title}")
                    
                    # Create questions and choices
                    for i, q_data in enumerate(data['questions']):
                        question = Question.objects.create(
                            quiz=quiz,
                            question_text=q_data['text'],
                            question_type=q_data['type'],
                            order=i + 1
                        )
                        
                        for j, c_data in enumerate(q_data['choices']):
                            Choice.objects.create(
                                question=question,
                                choice_text=c_data['text'],
                                is_correct=c_data['correct'],
                                order=j + 1
                            )
                        
                        self.stdout.write(f"   📝 Added question: {q_data['text'][:50]}...")
        
        self.stdout.write(f"\n🎯 Created {created_count} sample quizzes with questions!")
        self.stdout.write("📊 You can now access quizzes in Django Admin at /admin/ui/quiz/")