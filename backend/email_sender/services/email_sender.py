import smtplib
from email.message import EmailMessage

from core.config import get_settings

settings = get_settings()


class EmailSender:
    def send(self, *, to: str, subject: str, body: str) -> None:
        message = EmailMessage()

        message['From'] = settings.from_email
        message['To'] = to
        message['Subject'] = subject

        message.add_alternative(body, subtype='html')

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.starttls()

            smtp.login(settings.smtp_username, settings.smtp_password)

            smtp.send_message(message)
