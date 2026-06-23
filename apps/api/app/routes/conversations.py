import json
import uuid
from dataclasses import asdict
from queue import Queue
from threading import Thread
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_database_session
from app.domain.progress import OrchestrationProgress
from app.exceptions import (
    ChatServiceError,
    ContextBudgetError,
    ConversationBusyError,
    ConversationNotFoundError,
)
from app.providers.base import ChatProvider
from app.providers.factory import get_chat_provider
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationSummaryResponse,
)
from app.schemas.message import MessageCreate, MessageExchangeResponse
from app.services.conversation_chat_service import ConversationChatService

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]
ProviderDependency = Annotated[
    ChatProvider,
    Depends(get_chat_provider),
]


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    request: ConversationCreate,
    session: DatabaseSession,
) -> ConversationResponse:
    repository = ConversationRepository(session)

    return repository.create(title=request.title)


@router.get(
    "",
    response_model=list[ConversationSummaryResponse],
)
def list_conversations(
    session: DatabaseSession,
) -> list[ConversationSummaryResponse]:
    repository = ConversationRepository(session)

    return repository.list_recent()


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def get_conversation(
    conversation_id: uuid.UUID,
    session: DatabaseSession,
) -> ConversationResponse:
    repository = ConversationRepository(session)
    conversation = repository.get_by_id(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    return conversation


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageExchangeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    conversation_id: uuid.UUID,
    request: MessageCreate,
    session: DatabaseSession,
    provider: ProviderDependency,
) -> MessageExchangeResponse:
    service = ConversationChatService(
        session=session,
        provider=provider,
    )

    try:
        user_message, assistant_message, memory_status = service.respond(
            conversation_id=conversation_id,
            content=request.content,
        )
    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        ) from error
    except ConversationBusyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The conversation already has an active response.",
        ) from error
    except ContextBudgetError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except ChatServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    return MessageExchangeResponse(
        user_message=user_message,
        assistant_message=assistant_message,
        memory_update_status=memory_status,
    )


@router.post(
    "/{conversation_id}/messages/stream",
    response_class=StreamingResponse,
)
def stream_message(
    conversation_id: uuid.UUID,
    request: MessageCreate,
    provider: ProviderDependency,
) -> StreamingResponse:
    event_queue: Queue[dict[str, object] | None] = Queue()

    def publish_progress(event: OrchestrationProgress) -> None:
        event_queue.put(
            {
                "type": "progress",
                **asdict(event),
            }
        )

    def produce_response() -> None:
        with SessionLocal() as session:
            service = ConversationChatService(
                session=session,
                provider=provider,
            )

            try:
                user_message, assistant_message, memory_status = service.respond(
                    conversation_id=conversation_id,
                    content=request.content,
                    progress=publish_progress,
                )
                exchange = MessageExchangeResponse(
                    user_message=user_message,
                    assistant_message=assistant_message,
                    memory_update_status=memory_status,
                )
                event_queue.put(
                    {
                        "type": "complete",
                        "exchange": exchange.model_dump(mode="json"),
                    }
                )
            except ConversationNotFoundError:
                event_queue.put(
                    {
                        "type": "error",
                        "message": "Conversation not found.",
                    }
                )
            except ConversationBusyError:
                event_queue.put(
                    {
                        "type": "error",
                        "message": (
                            "The conversation already has an active response."
                        ),
                    }
                )
            except (ContextBudgetError, ChatServiceError) as error:
                event_queue.put(
                    {
                        "type": "error",
                        "message": str(error),
                    }
                )
            except Exception:
                event_queue.put(
                    {
                        "type": "error",
                        "message": (
                            "The Reliability Agent could not complete the "
                            "request."
                        ),
                    }
                )
            finally:
                event_queue.put(None)

    def generate_events():
        worker = Thread(
            target=produce_response,
            name=f"conversation-stream-{conversation_id}",
            daemon=True,
        )
        worker.start()

        while True:
            event = event_queue.get()
            if event is None:
                break

            yield f"{json.dumps(event)}\n"

    return StreamingResponse(
        generate_events(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
