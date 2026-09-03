import aio_pika
from aio_pika import (
    Connection,
    DeliveryMode,
)
from aio_pika.abc import AbstractChannel


class RabbitmqClient:
    def __init__(self, url: str) -> None:
        self._url = url
        self._connection: Connection | None = None
        self._channel: AbstractChannel | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()

    async def publish(self, message: bytes, *, exchange: str, routing_key: str) -> None:
        if self._channel is None:
            raise RuntimeError('RabbitMQ client is not connected')

        rabbitmq_exchange = await self._channel.get_exchange(exchange)

        await rabbitmq_exchange.publish(
            aio_pika.Message(
                body=message,
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=routing_key,
        )

    async def setup_topology(self) -> None:
        if self._channel is None:
            raise RuntimeError('RabbitMQ client is not connected')

        exchange = await self._channel.declare_exchange(
            'notifications',
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )

        queue = await self._channel.declare_queue(
            'email_queue',
            durable=True,
        )

        await queue.bind(
            exchange,
            routing_key='email',
        )
