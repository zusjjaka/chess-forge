import uuid

import aio_pika
import pytest

from clients.rabbitmq import RabbitmqClient


RABBITMQ_URL = 'amqp://guest:guest@localhost:5672/'


@pytest.mark.asyncio
async def test_rabbitmq_connect() -> None:
    client = RabbitmqClient(RABBITMQ_URL)

    await client.connect()

    try:
        assert client._connection is not None
        assert client._channel is not None
        assert not client._connection.is_closed
        assert not client._channel.is_closed
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_rabbitmq_setup_topology() -> None:
    client = RabbitmqClient(RABBITMQ_URL)

    await client.connect()

    try:
        await client.setup_topology()

        assert client._channel is not None

        exchange = await client._channel.get_exchange(
            'notifications',
        )
        queue = await client._channel.get_queue(
            'email_queue',
        )

        assert exchange.name == 'notifications'
        assert queue.name == 'email_queue'
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_rabbitmq_publish_and_consume() -> None:
    client = RabbitmqClient(RABBITMQ_URL)

    await client.connect()

    try:
        await client.setup_topology()

        assert client._channel is not None

        exchange = await client._channel.get_exchange(
            'notifications',
        )

        queue_name = f'test_email_{uuid.uuid4()}'

        queue = await client._channel.declare_queue(
            queue_name,
            exclusive=True,
            auto_delete=True,
        )

        await queue.bind(
            exchange,
            routing_key='email',
        )

        message_body = b'{"type":"email.verification","code":"123456"}'

        await client.publish(
            message=message_body,
            exchange='notifications',
            routing_key='email',
        )

        message = await queue.get(
            timeout=5,
            fail=False,
        )

        assert message is not None
        assert message.body == message_body
        assert message.delivery_mode == aio_pika.DeliveryMode.PERSISTENT

        await message.ack()

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_rabbitmq_publish_requires_connection() -> None:
    client = RabbitmqClient(RABBITMQ_URL)

    with pytest.raises(
        RuntimeError,
        match='RabbitMQ client is not connected',
    ):
        await client.publish(
            message=b'test',
            exchange='notifications',
            routing_key='email',
        )


@pytest.mark.asyncio
async def test_rabbitmq_topology_is_idempotent() -> None:
    client = RabbitmqClient(RABBITMQ_URL)

    await client.connect()

    try:
        await client.setup_topology()
        await client.setup_topology()

        assert client._channel is not None

        exchange = await client._channel.get_exchange(
            'notifications',
        )
        queue = await client._channel.get_queue(
            'email_queue',
        )

        assert exchange.name == 'notifications'
        assert queue.name == 'email_queue'

    finally:
        await client.close()
