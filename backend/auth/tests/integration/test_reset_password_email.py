import json
import uuid

import pytest
from sqlalchemy import select

from clients.rabbitmq import RabbitmqClient
from models.verification_code import PasswordResetCode
from publishers.email import EmailPublisher
from services.auth import AuthService


@pytest.mark.asyncio
async def test_password_reset_publishes_email(
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

        verification_message = await queue.get(
            timeout=5,
            fail=False,
        )

        assert verification_message is not None

        await service.request_password_reset(
            email=email,
        )

        message = await queue.get(
            timeout=5,
            fail=False,
        )

        assert message is not None

        payload = json.loads(message.body.decode())

        result = await session.execute(
            select(PasswordResetCode).where(
                PasswordResetCode.user_id == user.id,
            )
        )
        reset_code = result.scalar_one()

        assert payload['type'] == 'email.password_reset'
        assert payload['to'] == email
        assert payload['version'] == 1

        assert payload['message_id'] == str(
            reset_code.id,
        )

        assert set(payload['data']) == {'code'}
        assert len(payload['data']['code']) > 0

        assert reset_code.user_id == user.id
        assert reset_code.used_at is None

    finally:
        await rabbitmq.close()
