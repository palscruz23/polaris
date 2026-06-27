from typing import Annotated, Awaitable, Callable

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_database_session
from app.dependencies.auth import CurrentUser
from app.schemas.auth import AuthUserResponse
from app.services.auth_service import (
    REDIRECT_COOKIE_NAME,
    STATE_COOKIE_NAME,
    AuthConfigurationError,
    OAuthProfile,
    OAuthProviderError,
    OAuthRedirectError,
    OAuthStateError,
    build_state_token,
    create_user_session,
    delete_session_token,
    exchange_google_code,
    exchange_microsoft_code,
    frontend_redirect_url,
    google_authorization_url,
    microsoft_authorization_url,
    safe_redirect_path,
    upsert_oauth_user,
    verify_state_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
ProfileExchanger = Callable[[str], Awaitable[OAuthProfile]]


@router.get("/google/login")
def login_with_google(next: str | None = None) -> RedirectResponse:
    return _login_redirect(google_authorization_url, next)


@router.get("/microsoft/login")
def login_with_microsoft(next: str | None = None) -> RedirectResponse:
    return _login_redirect(microsoft_authorization_url, next)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    session: DatabaseSession,
    expected_state: Annotated[str | None, Cookie(alias=STATE_COOKIE_NAME)] = None,
    redirect_path: Annotated[
        str | None,
        Cookie(alias=REDIRECT_COOKIE_NAME),
    ] = None,
) -> RedirectResponse:
    return await _handle_callback(
        code=code,
        received_state=state,
        expected_state=expected_state,
        redirect_path=redirect_path,
        session=session,
        exchange_profile=exchange_google_code,
    )


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str,
    state: str,
    session: DatabaseSession,
    expected_state: Annotated[str | None, Cookie(alias=STATE_COOKIE_NAME)] = None,
    redirect_path: Annotated[
        str | None,
        Cookie(alias=REDIRECT_COOKIE_NAME),
    ] = None,
) -> RedirectResponse:
    return await _handle_callback(
        code=code,
        received_state=state,
        expected_state=expected_state,
        redirect_path=redirect_path,
        session=session,
        exchange_profile=exchange_microsoft_code,
    )


@router.get("/me", response_model=AuthUserResponse)
def get_me(user: CurrentUser) -> AuthUserResponse:
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session: DatabaseSession,
    session_token: Annotated[
        str | None,
        Cookie(alias=settings.auth_session_cookie_name),
    ] = None,
) -> Response:
    delete_session_token(session, session_token)
    _delete_session_cookie(response)
    return response


def _login_redirect(
    authorization_url_builder: Callable[[str], str],
    next_path: str | None,
) -> RedirectResponse:
    state = build_state_token()

    try:
        authorization_url = authorization_url_builder(state)
    except AuthConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    response = RedirectResponse(authorization_url)
    response.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        max_age=600,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )
    if redirect_path := safe_redirect_path(next_path):
        response.set_cookie(
            key=REDIRECT_COOKIE_NAME,
            value=redirect_path,
            httponly=True,
            max_age=600,
            secure=settings.auth_cookie_secure,
            samesite="lax",
        )
    return response


async def _handle_callback(
    code: str,
    received_state: str,
    expected_state: str | None,
    redirect_path: str | None,
    session: Session,
    exchange_profile: ProfileExchanger,
) -> RedirectResponse:
    try:
        verify_state_token(expected_state, received_state)
        redirect_url = frontend_redirect_url(redirect_path)
        profile = await exchange_profile(code)
    except OAuthStateError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except OAuthRedirectError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except AuthConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except (OAuthProviderError, httpx.HTTPError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OAuth provider sign-in failed.",
        ) from error

    user = upsert_oauth_user(session, profile)
    _, session_token = create_user_session(session, user)

    response = RedirectResponse(redirect_url)
    response.delete_cookie(STATE_COOKIE_NAME, httponly=True, samesite="lax")
    response.delete_cookie(REDIRECT_COOKIE_NAME, httponly=True, samesite="lax")
    response.set_cookie(
        key=settings.auth_session_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.auth_session_days * 24 * 60 * 60,
    )
    return response


def _delete_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth_session_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )
