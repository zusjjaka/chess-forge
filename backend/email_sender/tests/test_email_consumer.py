import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from consumers.email import handle_message
from core.config import get_settings


settings = get_settings()


class FakeMessage:
    def __init__(self, body: bytes) -> None:
        self.body = body

        self.process_context = MagicMock()
        self.process_context.__aenter__ = AsyncMock(
            return_value=self,
        )
        self.process_context.__aexit__ = AsyncMock(
            return_value=None,
        )

    def process(self) -> MagicMock:
        return self.process_context


def make_message(
    *,
    message_type: str = 'email.verification',
    to: str = 'user@example.com',
    data: dict[str, str] | None = None,
) -> FakeMessage:
    if data is None:
        data = {
            'code': '123456',
        }

    payload = {
        'type': message_type,
        'to': to,
        'data': data,
        'message_id': str(uuid.uuid4()),
        'version': 1,
    }

    return FakeMessage(
        json.dumps(payload).encode(),
    )


@pytest.mark.asyncio
@patch('consumers.email.EmailSender')
@patch('consumers.email.TemplateRenderer')
async def test_handle_verification_email(
    renderer_class: MagicMock,
    sender_class: MagicMock,
) -> None:
    renderer = MagicMock()
    renderer.render.return_value = '<h1>Verification</h1>'
    renderer_class.return_value = renderer

    sender = MagicMock()
    sender_class.return_value = sender

    message = make_message(
        data={
            'code': '123456',
        },
    )

    await handle_message(message)

    renderer.render.assert_called_once_with(
        template_name='email_verification.html',
        code='123456',
    )

    sender.send.assert_called_once_with(
        to='user@example.com',
        subject='ChessForge - Email Verification',
        body='<h1>Verification</h1>',
    )

    message.process_context.__aenter__.assert_awaited_once()
    message.process_context.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
@patch('consumers.email.EmailSender')
@patch('consumers.email.TemplateRenderer')
async def test_handle_password_reset_email(
    renderer_class: MagicMock,
    sender_class: MagicMock,
) -> None:
    renderer = MagicMock()
    renderer.render.return_value = '<h1>Password Reset</h1>'
    renderer_class.return_value = renderer

    sender = MagicMock()
    sender_class.return_value = sender

    message = make_message(
        message_type='email.password_reset',
        data={
            'code': '654321',
        },
    )

    await handle_message(message)

    renderer.render.assert_called_once_with(
        template_name='password_reset.html',
        code='654321',
    )

    sender.send.assert_called_once_with(
        to='user@example.com',
        subject='ChessForge - Password Reset',
        body='<h1>Password Reset</h1>',
    )

    message.process_context.__aenter__.assert_awaited_once()
    message.process_context.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_rejects_invalid_json() -> None:
    message = FakeMessage(
        b'not valid json',
    )

    with pytest.raises(ValidationError):
        await handle_message(message)


@pytest.mark.asyncio
async def test_handle_message_rejects_unknown_email_type() -> None:
    message = make_message(
        message_type='email.unknown',
    )

    with pytest.raises(ValidationError, match='email.unknown'):
        await handle_message(message)


@pytest.mark.asyncio
@patch('consumers.email.EmailSender')
@patch('consumers.email.TemplateRenderer')
async def test_handle_message_propagates_render_error(
    renderer_class: MagicMock,
    sender_class: MagicMock,
) -> None:
    renderer = MagicMock()
    renderer.render.side_effect = RuntimeError('Template error')
    renderer_class.return_value = renderer

    message = make_message()

    with pytest.raises(RuntimeError, match='Template error'):
        await handle_message(message)

    sender_class.return_value.send.assert_not_called()


@pytest.mark.asyncio
@patch('consumers.email.EmailSender')
@patch('consumers.email.TemplateRenderer')
async def test_handle_message_propagates_send_error(
    renderer_class: MagicMock,
    sender_class: MagicMock,
) -> None:
    renderer = MagicMock()
    renderer.render.return_value = '<p>Verification</p>'
    renderer_class.return_value = renderer

    sender = MagicMock()
    sender.send.side_effect = OSError('SMTP error')
    sender_class.return_value = sender

    message = make_message()

    with pytest.raises(OSError, match='SMTP error'):
        await handle_message(message)

    renderer.render.assert_called_once()

    sender.send.assert_called_once()


@pytest.mark.asyncio
@patch('consumers.email.EmailSender')
@patch('consumers.email.TemplateRenderer')
async def test_handle_message_passes_exception_to_process_context(
    renderer_class: MagicMock,
    sender_class: MagicMock,
) -> None:
    renderer = MagicMock()
    renderer.render.side_effect = RuntimeError('Template error')
    renderer_class.return_value = renderer

    message = make_message()

    with pytest.raises(RuntimeError, match='Template error'):
        await handle_message(message)

    message.process_context.__aexit__.assert_awaited_once()

    args = message.process_context.__aexit__.call_args.args

    assert args[0] is RuntimeError
    assert isinstance(args[1], RuntimeError)
    assert args[1].args == ('Template error',)

    sender_class.return_value.send.assert_not_called()


@pytest.mark.asyncio
@patch('consumers.email.EmailSender')
@patch('consumers.email.TemplateRenderer')
async def test_handle_email_change_email(
    renderer_class: MagicMock,
    sender_class: MagicMock,
) -> None:
    renderer = MagicMock()
    renderer.render.return_value = '<h1>Email Change</h1>'
    renderer_class.return_value = renderer

    sender = MagicMock()
    sender_class.return_value = sender

    message = make_message(
        message_type='email.change',
        to='new@example.com',
        data={
            'code': '123456',
        },
    )

    await handle_message(message)

    renderer.render.assert_called_once_with(
        template_name='email_change.html',
        code='123456',
    )

    sender.send.assert_called_once_with(
        to='new@example.com',
        subject='ChessForge - Email Change',
        body='<h1>Email Change</h1>',
    )

    message.process_context.__aenter__.assert_awaited_once()
    message.process_context.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
@patch('consumers.email.asyncio.Future')
@patch('consumers.email.aio_pika.connect_robust')
async def test_consume(
    connect_robust: AsyncMock,
    future_class: MagicMock,
) -> None:
    connection = AsyncMock()
    channel = AsyncMock()
    queue = AsyncMock()

    connection.channel.return_value = channel
    channel.declare_queue.return_value = queue

    connect_robust.return_value = connection

    future_class.side_effect = RuntimeError('Stop consumer')

    from consumers.email import consume

    with pytest.raises(RuntimeError, match='Stop consumer'):
        await consume()

    connect_robust.assert_awaited_once()

    connection.channel.assert_awaited_once()

    channel.set_qos.assert_awaited_once_with(
        prefetch_count=1,
    )

    channel.declare_queue.assert_awaited_once_with(
        settings.rabbitmq.queue,
        durable=True,
    )

    queue.consume.assert_awaited_once_with(
        handle_message,
    )
