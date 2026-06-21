import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Conversation
from app.models.conversation_memory_revision import ConversationMemoryRevision


class ConversationRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, title: str | None = None) -> Conversation:
        conversation = Conversation(title=title)

        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)

        return conversation

    def get_by_id(
        self,
        conversation_id: uuid.UUID,
    ) -> Conversation | None:
        statement = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )

        return self.session.scalar(statement)

    def get_for_update(
        self,
        conversation_id: uuid.UUID,
    ) -> Conversation | None:
        statement = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .with_for_update()
        )

        return self.session.scalar(statement)

    def save_memory(
        self,
        conversation: Conversation,
        memory_markdown: str,
        through_sequence_number: int,
    ) -> ConversationMemoryRevision:
        revision = ConversationMemoryRevision(
            conversation_id=conversation.id,
            memory_markdown=memory_markdown,
            through_sequence_number=through_sequence_number,
        )

        conversation.memory_markdown = memory_markdown
        conversation.memory_through_sequence_number = through_sequence_number
        conversation.memory_updated_at = datetime.now(UTC)
        conversation.memory_update_status = "completed"
        conversation.memory_update_error = None

        self.session.add(revision)
        self.session.commit()
        self.session.refresh(revision)

        return revision

    def begin_processing(
        self,
        conversation: Conversation,
    ) -> None:
        conversation.is_processing = True
        conversation.processing_started_at = datetime.now(UTC)
        self.session.commit()

    def end_processing(
        self,
        conversation: Conversation,
    ) -> None:
        conversation.is_processing = False
        conversation.processing_started_at = None
        self.session.commit()

    def mark_memory_update_pending(
        self,
        conversation: Conversation,
    ) -> None:
        conversation.memory_update_status = "pending"
        conversation.memory_update_error = None
        self.session.commit()

    def mark_memory_update_failed(
        self,
        conversation: Conversation,
        error_message: str,
    ) -> None:
        conversation.memory_update_status = "failed"
        conversation.memory_update_error = error_message
        self.session.commit()
