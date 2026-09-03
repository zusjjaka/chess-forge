import json
import uuid
from unittest.mock import AsyncMock

import pytest

from clients.rabbitmq import RabbitmqClient
from publishers.email import EmailPublisher


@pytest.mark.asyncio
async def test_publish_email_verification() -> None:
    rabbitmq = AsyncMock(spec=RabbitmqClient)
    publisher = EmailPublisher(rabbitmq)

    message_id = uuid.uuid4()

    await publisher.publish_email_verification(
        email='user@example.com',
        code='123456',
        message_id=message_id,
    )

    rabbitmq.publish.assert_awaited_once()

    kwargs = rabbitmq.publish.await_args.kwargs

    assert kwargs['exchange'] == EmailPublisher.EXCHANGE
    assert kwargs['routing_key'] == EmailPublisher.ROUTING_KEY

    message = json.loads(kwargs['message'].decode())

    assert message == {
        'type': 'email.verification',
        'to': 'user@example.com',
        'data': {
            'code': '123456',
        },
        'message_id': str(message_id),
        'version': 1,
    }


@pytest.mark.asyncio
async def test_publish_email_verification_propagates_rabbitmq_error() -> None:
    rabbitmq = AsyncMock(spec=RabbitmqClient)
    rabbitmq.publish.side_effect = RuntimeError(
        'RabbitMQ unavailable',
    )

    publisher = EmailPublisher(rabbitmq)

    with pytest.raises(
        RuntimeError,
        match='RabbitMQ unavailable',
    ):
        await publisher.publish_email_verification(
            email='user@example.com',
            code='123456',
            message_id=uuid.uuid4(),
        )
