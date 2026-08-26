from celery import Celery

from .config import get_settings

settings = get_settings()

celery_app = Celery(
    'email_sender', broker=settings.celery_broker_url, include=('tasks.email',)
)
