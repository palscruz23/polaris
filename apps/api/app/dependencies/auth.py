from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_database_session
from app.models.user import User
from app.services.auth_service import get_user_by_session_token


DatabaseSession = Annotated[Session, Depends(get_database_session)]


def get_current_user(
    session: DatabaseSession,
    session_token: Annotated[
        str | None,
        Cookie(alias=settings.auth_session_cookie_name),
    ] = None,
) -> User:
    user = get_user_by_session_token(session, session_token)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
