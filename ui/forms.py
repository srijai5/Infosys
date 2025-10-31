# forms.py
from django import forms
from .models import Course

class CourseForm(forms.ModelForm):
    youtube_links = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'YouTube URLs separated by commas...',
            'rows': 2,
            'class': 'w-full px-3 py-1.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition'
        }),
        help_text="Separate multiple URLs with commas."
    )
    
    video_titles = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'Video titles separated by commas (in same order as URLs)...',
            'rows': 2,
            'class': 'w-full px-3 py-1.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition'
        }),
        help_text="Provide titles for each video in the same order as URLs."
    )

    class Meta:
        model = Course
        fields = ['course_name', 'duration_weeks', 'image', 'description', 'youtube_links', 'video_titles']
        widgets = {
            'course_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-1.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition',
                'placeholder': 'Enter course name'
            }),
            'duration_weeks': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-1.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition',
                'placeholder': 'Duration in weeks'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'w-full text-gray-700 border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-1.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition',
                'rows': 3,
                'placeholder': 'Write a brief description of the course'
            }),
        }

    def clean_youtube_links(self):
        data = self.cleaned_data.get('youtube_links', '')
        if not data:
            return []
        urls = [url.strip() for url in data.split(',') if url.strip()]
        for url in urls:
            if not (url.startswith('https://') or url.startswith('http://')):
                raise forms.ValidationError(f"Invalid URL: {url}")
        return urls

    def clean_video_titles(self):
        data = self.cleaned_data.get('video_titles', '')
        if not data:
            return []
        titles = [title.strip() for title in data.split(',') if title.strip()]
        return titles

    def clean(self):
        cleaned_data = super().clean()
        youtube_links = cleaned_data.get('youtube_links', [])
        video_titles = cleaned_data.get('video_titles', [])
        
        # If both fields are provided, they should have the same number of items
        if youtube_links and video_titles:
            if len(youtube_links) != len(video_titles):
                raise forms.ValidationError(
                    "Number of YouTube URLs must match number of video titles."
                )
        
        return cleaned_data