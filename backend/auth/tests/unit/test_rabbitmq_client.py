from unittest.mock import AsyncMock, MagicMock, patch

import aio_pika
import pytest

from clients.rabbitmq import RabbitmqClient


@pytest.fixture
def client() -> RabbitmqClient:
    return RabbitmqClient('amqp://user:password@localhost:5672/')


@pytest.mark.asyncio
async def test_connect(client: RabbitmqClient) -> None:
    connection = AsyncMock()
    channel = AsyncMock()

    connection.channel.return_value = channel

    with patch(
        'clients.rabbitmq.aio_pika.connect_robust',
        new_callable=AsyncMock,
        return_value=connection,
    ) as connect:
        await client.connect()

    connect.assert_awaited_once_with(
        'amqp://user:password@localhost:5672/',
    )
    connection.channel.assert_awaited_once()

    assert client._connection is connection
    assert client._channel is channel


@pytest.mark.asyncio
async def test_close_when_connected(client: RabbitmqClient) -> None:
    connection = AsyncMock()
    client._connection = connection

    await client.close()

    connection.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_when_not_connected(
    client: RabbitmqClient,
) -> None:
    await client.close()


@pytest.mark.asyncio
async def test_publish_when_not_connected(
    client: RabbitmqClient,
) -> None:
    with pytest.raises(
        RuntimeError,
        match='RabbitMQ client is not connected',
    ):
        await client.publish(
            message=b'test-message',
            exchange='notifications',
            routing_key='email',
        )


@pytest.mark.asyncio
async def test_publish(
    client: RabbitmqClient,
) -> None:
    channel = AsyncMock()
    exchange = AsyncMock()

    channel.get_exchange.return_value = exchange
    client._channel = channel

    message = b'{"test": "message"}'

    await client.publish(
        message=message,
        exchange='notifications',
        routing_key='email',
    )

    channel.get_exchange.assert_awaited_once_with(
        'notifications',
    )

    exchange.publish.assert_awaited_once()

    published_message = exchange.publish.await_args.args[0]

    assert published_message.body == message
    assert (
        published_message.delivery_mode
        == aio_pika.DeliveryMode.PERSISTENT
    )

    assert exchange.publish.await_args.kwargs['routing_key'] == 'email'


@pytest.mark.asyncio
async def test_publish_propagates_exchange_error(
    client: RabbitmqClient,
) -> None:
    channel = AsyncMock()
    channel.get_exchange.side_effect = RuntimeError(
        'RabbitMQ unavailable',
    )

    client._channel = channel

    with pytest.raises(
        RuntimeError,
        match='RabbitMQ unavailable',
    ):
        await client.publish(
            message=b'test-message',
            exchange='notifications',
            routing_key='email',
        )


@pytest.mark.asyncio
async def test_setup_topology_when_not_connected(
    client: RabbitmqClient,
) -> None:
    with pytest.raises(
        RuntimeError,
        match='RabbitMQ client is not connected',
    ):
        await client.setup_topology()


@pytest.mark.asyncio
async def test_setup_topology(
    client: RabbitmqClient,
) -> None:
    channel = AsyncMock()
    exchange = AsyncMock()
    queue = AsyncMock()

    channel.declare_exchange.return_value = exchange
    channel.declare_queue.return_value = queue

    client._channel = channel

    await client.setup_topology()

    channel.declare_exchange.assert_awaited_once_with(
        'notifications',
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    channel.declare_queue.assert_awaited_once_with(
        'email_queue',
        durable=True,
    )

    queue.bind.assert_awaited_once_with(
        exchange,
        routing_key='email',
    )


@pytest.mark.asyncio
async def test_setup_topology_propagates_exchange_error(
    client: RabbitmqClient,
) -> None:
    channel = AsyncMock()
    channel.declare_exchange.side_effect = RuntimeError(
        'RabbitMQ unavailable',
    )

    client._channel = channel

    with pytest.raises(
        RuntimeError,
        match='RabbitMQ unavailable',
    ):
        await client.setup_topology()


@pytest.mark.asyncio
async def test_setup_topology_propagates_queue_error(
    client: RabbitmqClient,
) -> None:
    channel = AsyncMock()
    exchange = MagicMock()

    channel.declare_exchange.return_value = exchange
    channel.declare_queue.side_effect = RuntimeError(
        'Queue declaration failed',
    )

    client._channel = channel

    with pytest.raises(
        RuntimeError,
        match='Queue declaration failed',
    ):
        await client.setup_topology()
