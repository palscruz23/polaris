import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.chat import ChatMessage
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole


class MessageRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        conversation: Conversation,
        role: MessageRole,
        content: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> Message:
        sequence_number = conversation.message_count + 1

        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            sequence_number=sequence_number,
            provider=provider,
            model=model,
        )

        conversation.message_count = sequence_number

        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)

        return message

    def list_for_conversation(
        self,
        conversation_id: uuid.UUID,
        *,
        through_sequence_number: int | None = None,
    ) -> Sequence[Message]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_number)
        )

        if through_sequence_number is not None:
            statement = statement.where(
                Message.sequence_number <= through_sequence_number
            )

        return self.session.scalars(statement).all()

    def list_after_sequence(
        self,
        conversation_id: uuid.UUID,
        sequence_number: int,
    ) -> Sequence[Message]:
        statement = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sequence_number > sequence_number,
            )
            .order_by(Message.sequence_number)
        )

        return self.session.scalars(statement).all()

    @staticmethod
    def to_chat_messages(
        messages: Sequence[Message],
    ) -> list[ChatMessage]:
        return [
            ChatMessage(role=message.role, content=message.content)
            for message in messages
        ]
