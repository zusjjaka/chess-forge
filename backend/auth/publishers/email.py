import uuid

from clients.rabbitmq import RabbitmqClient
from schemas.email import (
    EmailMessage,
    EmailMessageType,
)


class EmailPublisher:
    EXCHANGE = 'notifications'
    ROUTING_KEY = 'email'

    def __init__(self, rabbitmq: RabbitmqClient) -> None:
        self.rabbitmq = rabbitmq

    async def publish_email_verification(
        self, email: str, code: str, message_id: uuid.UUID
    ) -> None:
        await self._publish(
            msg_id=message_id,
            msg_type='email.verification',
            usr_email=email,
            data={'code': code},
        )

    async def _publish(
        self,
        msg_id: uuid.UUID,
        msg_type: EmailMessageType,
        usr_email: str,
        data: dict[str, str],
    ) -> None:
        message: EmailMessage = EmailMessage(
            type=msg_type, to=usr_email, data=data, message_id=msg_id, version=1
        )

        await self.rabbitmq.publish(
            message=message.model_dump_json().encode(),
            exchange=self.EXCHANGE,
            routing_key=self.ROUTING_KEY,
        )
