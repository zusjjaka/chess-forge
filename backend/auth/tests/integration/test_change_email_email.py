import json
import uuid

import pytest
from sqlalchemy import select

from clients.rabbitmq import RabbitmqClient
from models.verification_code import EmailChangeCode
from publishers.email import EmailPublisher
from services.auth import AuthService


@pytest.mark.asyncio
async def test_email_change_publishes_email(
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
        new_email = f'{uuid.uuid4()}@example.com'
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

        user.is_email_verified = True
        await session.commit()

        await service.request_email_change(
            user_id=user.id,
            new_email=new_email,
            password=password,
        )

        message = await queue.get(
            timeout=5,
            fail=False,
        )

        assert message is not None

        payload = json.loads(message.body.decode())

        result = await session.execute(
            select(EmailChangeCode).where(
                EmailChangeCode.user_id == user.id,
            )
        )
        email_change_code = result.scalar_one()

        assert payload['type'] == 'email.change'
        assert payload['to'] == new_email
        assert payload['version'] == 1

        assert payload['message_id'] == str(
            email_change_code.id,
        )

        assert set(payload['data']) == {'code'}
        assert len(payload['data']['code']) > 0

        assert email_change_code.user_id == user.id
        assert email_change_code.new_email == new_email
        assert email_change_code.used_at is None

    finally:
        await rabbitmq.close()
