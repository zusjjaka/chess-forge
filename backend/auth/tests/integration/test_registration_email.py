import json
import uuid

import aio_pika
import pytest
from sqlalchemy import select

from clients.rabbitmq import RabbitmqClient
from core.config import get_settings
from models.verification_code import EmailVerificationCode
from publishers.email import EmailPublisher
from services.auth import AuthService


@pytest.mark.asyncio
async def test_registration_publishes_email_verification(
    session,
) -> None:
    rabbitmq = RabbitmqClient('amqp://guest:guest@localhost:5672/')
    await rabbitmq.connect()
    await rabbitmq.setup_topology()

    try:
        channel = rabbitmq._channel
        assert channel is not None

        exchange = await channel.get_exchange(
            EmailPublisher.EXCHANGE,
        )

        queue = await channel.declare_queue(
            name=f'test_email_{uuid.uuid4()}',
            exclusive=True,
            auto_delete=True,
        )

        await queue.bind(
            exchange,
            routing_key=EmailPublisher.ROUTING_KEY,
        )

        publisher = EmailPublisher(rabbitmq)
        service = AuthService(
            session=session,
            email_publisher=publisher,
        )

        email = f'{uuid.uuid4()}@example.com'
        password = 'StrongPassword123!'

        user = await service.register(
            email=email,
            password=password,
        )

        message = await queue.get(
            timeout=5,
            fail=False,
        )

        assert message is not None

        payload = json.loads(message.body.decode())

        result = await session.execute(
            select(EmailVerificationCode).where(
                EmailVerificationCode.user_id == user.id,
            )
        )
        verification_code = result.scalar_one()

        assert payload['type'] == 'email.verification'
        assert payload['to'] == email
        assert payload['version'] == 1

        assert payload['message_id'] == str(
            verification_code.id,
        )

        assert set(payload['data']) == {'code'}
        assert len(payload['data']['code']) > 0

        assert verification_code.user_id == user.id
        assert verification_code.used_at is None

    finally:
        await rabbitmq.close()
