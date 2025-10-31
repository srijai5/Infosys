# In your_app/templatetags/youtube_filters.py
import re
from django import template

register = template.Library()

@register.filter
def youtube_id(url):
    """Extract YouTube ID from URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&?#]+)',
        r'youtube\.com\/v\/([^&?#]+)',
        r'youtube\.com\/watch\?.+&v=([^&?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match and match.group(1):
            return match.group(1)
    return ''