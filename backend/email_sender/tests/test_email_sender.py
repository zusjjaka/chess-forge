from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest

from services.email_sender import EmailSender


@pytest.fixture
def smtp() -> MagicMock:
    smtp = MagicMock()

    smtp_context = MagicMock()
    smtp_context.__enter__.return_value = smtp
    smtp_context.__exit__.return_value = None

    smtp.return_value = smtp_context

    return smtp


@patch('services.email_sender.smtplib.SMTP')
def test_send_email(
    smtp_class: MagicMock,
) -> None:
    smtp = MagicMock()

    smtp_context = MagicMock()
    smtp_context.__enter__.return_value = smtp
    smtp_context.__exit__.return_value = None

    smtp_class.return_value = smtp_context

    sender = EmailSender()

    sender.send(
        to='user@example.com',
        subject='Test subject',
        body='<h1>Hello</h1>',
    )

    smtp_class.assert_called_once()

    smtp.starttls.assert_called_once()

    smtp.login.assert_called_once()

    smtp.send_message.assert_called_once()

    message = smtp.send_message.call_args.args[0]

    assert isinstance(message, EmailMessage)
    assert message['To'] == 'user@example.com'
    assert message['Subject'] == 'Test subject'
    assert message['From']

    assert '<h1>Hello</h1>' in message.as_string()


@patch('services.email_sender.smtplib.SMTP')
def test_send_email_uses_configured_smtp(
    smtp_class: MagicMock,
) -> None:
    smtp = MagicMock()

    smtp_context = MagicMock()
    smtp_context.__enter__.return_value = smtp
    smtp_context.__exit__.return_value = None

    smtp_class.return_value = smtp_context

    sender = EmailSender()

    sender.send(
        to='user@example.com',
        subject='Subject',
        body='<p>Body</p>',
    )

    from services.email_sender import settings

    smtp_class.assert_called_once_with(
        settings.smtp_host,
        settings.smtp_port,
    )

    smtp.login.assert_called_once_with(
        settings.smtp_username,
        settings.smtp_password,
    )


@patch('services.email_sender.smtplib.SMTP')
def test_send_email_sends_html_body(
    smtp_class: MagicMock,
) -> None:
    smtp = MagicMock()

    smtp_context = MagicMock()
    smtp_context.__enter__.return_value = smtp
    smtp_context.__exit__.return_value = None

    smtp_class.return_value = smtp_context

    sender = EmailSender()

    body = '<html><body><h1>Verification</h1></body></html>'

    sender.send(
        to='user@example.com',
        subject='Verification',
        body=body,
    )

    message = smtp.send_message.call_args.args[0]

    assert message.get_content_type() == 'multipart/alternative'

    html_part = next(
        part
        for part in message.iter_parts()
        if part.get_content_type() == 'text/html'
    )

    assert html_part.get_content().strip() == body


@patch('services.email_sender.smtplib.SMTP')
def test_send_email_propagates_smtp_error(
    smtp_class: MagicMock,
) -> None:
    smtp = MagicMock()

    smtp_context = MagicMock()
    smtp_context.__enter__.return_value = smtp
    smtp_context.__exit__.return_value = None

    smtp_class.return_value = smtp_context

    smtp.send_message.side_effect = OSError('SMTP error')

    sender = EmailSender()

    with pytest.raises(OSError, match='SMTP error'):
        sender.send(
            to='user@example.com',
            subject='Subject',
            body='<p>Body</p>',
        )
