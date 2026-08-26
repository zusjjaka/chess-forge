import smtplib
from email.message import EmailMessage

from core.config import Settings


class EmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, *, to: str, subject: str, body: str) -> None:
        message = EmailMessage()

        message['From'] = self._settings.from_email
        message['To'] = to
        message['Subject'] = subject

        message.set_content(body)

        smtp_config = (
            self._settings.smtp_host,
            self._settings.smtp_port,
        )

        with smtplib.SMTP(*smtp_config) as smtp:
            smtp.starttls()

            smtp.login(
                self._settings.smtp_username,
                self._settings.smtp_password,
            )

            smtp.send_message(message)
