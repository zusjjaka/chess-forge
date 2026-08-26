import smtplib
from unittest.mock import MagicMock, patch

import pytest

from core.config import Settings
from services.email_sender import EmailSender


def create_settings() -> Settings:
    return Settings(
        debug=True,
        smtp_host='sandbox.smtp.mailtrap.io',
        smtp_port=2525,
        smtp_username='username',
        smtp_password='password',
        from_email='sender@example.com',
        celery_broker_url='amqp://localhost:5672//',
    )


@patch('services.email_sender.smtplib.SMTP')
def test_send_email(mock_smtp: MagicMock) -> None:
    settings = create_settings()
    sender = EmailSender(settings)

    sender.send(
        to='recipient@example.com',
        subject='Test subject',
        body='Test body',
    )

    mock_smtp.assert_called_once_with(
        'sandbox.smtp.mailtrap.io',
        2525,
    )

    smtp = mock_smtp.return_value.__enter__.return_value

    smtp.starttls.assert_called_once_with()

    smtp.login.assert_called_once_with(
        'username',
        'password',
    )

    smtp.send_message.assert_called_once()


@patch('services.email_sender.smtplib.SMTP')
def test_send_email_creates_correct_message(
    mock_smtp: MagicMock,
) -> None:
    settings = create_settings()
    sender = EmailSender(settings)

    sender.send(
        to='recipient@example.com',
        subject='Test subject',
        body='Test body',
    )

    smtp = mock_smtp.return_value.__enter__.return_value
    message = smtp.send_message.call_args.args[0]

    assert message['From'] == 'sender@example.com'
    assert message['To'] == 'recipient@example.com'
    assert message['Subject'] == 'Test subject'
    assert message.get_content() == 'Test body\n'


@patch('services.email_sender.smtplib.SMTP')
def test_send_email_propagates_smtp_exception(
    mock_smtp: MagicMock,
) -> None:
    settings = create_settings()
    sender = EmailSender(settings)

    smtp = mock_smtp.return_value.__enter__.return_value
    smtp.send_message.side_effect = smtplib.SMTPException(
        'SMTP error',
    )

    with pytest.raises(smtplib.SMTPException):
        sender.send(
            to='recipient@example.com',
            subject='Test subject',
            body='Test body',
        )


@patch('services.email_sender.smtplib.SMTP')
def test_send_email_propagates_connection_error(
    mock_smtp: MagicMock,
) -> None:
    settings = create_settings()
    sender = EmailSender(settings)

    mock_smtp.side_effect = OSError('Connection failed')

    with pytest.raises(OSError):
        sender.send(
            to='recipient@example.com',
            subject='Test subject',
            body='Test body',
        )
