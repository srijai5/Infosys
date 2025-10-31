import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infosys.settings')

app = Celery('infosys')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()