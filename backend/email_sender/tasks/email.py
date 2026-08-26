import smtplib

from core.celery import celery_app
from core.config import get_settings
from services.email_sender import EmailSender


@celery_app.task(
    bind=True,
    autoretry_for=(smtplib.SMTPException, OSError),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def send_email(*, to: str, subject: str, body: str) -> None:
    settings = get_settings()
    sender = EmailSender(settings)

    sender.send(to=to, subject=subject, body=body)
