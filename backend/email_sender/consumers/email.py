import asyncio

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from core.config import get_settings
from schemas.email import EmailMessage
from services.email_sender import EmailSender
from services.template_renderer import TemplateRenderer

EMAIL_TYPES: dict[str, tuple[str, str]] = {
    'email.verification': (
        'email_verification.html',
        'ChessForge - Email Verification',
    ),
    'email.password_reset': (
        'password_reset.html',
        'ChessForge - Password Reset',
    ),
    'email.change': (
        'email_change.html',
        'ChessForge - Email Change',
    ),
}

settings = get_settings()


async def handle_message(message: AbstractIncomingMessage) -> None:
    async with message.process():
        payload: EmailMessage = EmailMessage.model_validate_json(message.body)

        html_msg_params: tuple[str, str] | None = EMAIL_TYPES.get(payload.type)

        if html_msg_params is None:
            raise ValueError(f'Unsupported email type: {payload.type}')

        template_name, subject = html_msg_params

        body = TemplateRenderer().render(template_name=template_name, **payload.data)

        EmailSender().send(to=payload.to, subject=subject, body=body)


async def consume() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq.url)

    channel = await connection.channel()

    await channel.set_qos(prefetch_count=1)

    queue = await channel.declare_queue(
        settings.rabbitmq.queue,
        durable=True,
    )

    await queue.consume(handle_message)

    await asyncio.Future()
