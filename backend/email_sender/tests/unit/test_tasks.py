from unittest.mock import MagicMock, patch

import pytest

from tasks.email import send_email


@patch('tasks.email.EmailSender')
def test_send_email_task(mock_email_sender: MagicMock) -> None:
    mock_sender = mock_email_sender.return_value

    send_email(
        to='recipient@example.com',
        subject='Test subject',
        body='Test body',
    )

    mock_email_sender.assert_called_once()

    mock_sender.send.assert_called_once_with(
        to='recipient@example.com',
        subject='Test subject',
        body='Test body',
    )


@patch('tasks.email.EmailSender')
def test_send_email_task_propagates_exception(
    mock_email_sender: MagicMock,
) -> None:
    mock_sender = mock_email_sender.return_value
    mock_sender.send.side_effect = OSError('SMTP connection failed')

    with pytest.raises(OSError):
        send_email(
            to='recipient@example.com',
            subject='Test subject',
            body='Test body',
        )
