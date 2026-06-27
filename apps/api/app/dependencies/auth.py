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


def user_is_admin(
    user: User,
    admin_emails: tuple[str, ...] | None = None,
) -> bool:
    configured_admin_emails = (
        settings.admin_emails
        if admin_emails is None
        else admin_emails
    )

    if not configured_admin_emails:
        return False

    return user.email.strip().lower() in configured_admin_emails


def get_current_admin_user(user: CurrentUser) -> User:
    if not user_is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    return user


CurrentAdminUser = Annotated[User, Depends(get_current_admin_user)]
