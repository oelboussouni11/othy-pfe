import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_token, decode_token
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, UserOut
from app.services.auth import AuthError, authenticate, register_user

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_BASE = {
    "httponly": True,
    "samesite": "lax",
    "secure": settings.environment != "development",
    "path": "/",
}


def _set_auth_cookies(response: Response, user_id: str) -> None:
    access = create_token(user_id, "access")
    refresh = create_token(user_id, "refresh")
    response.set_cookie(
        "access_token",
        access,
        max_age=settings.jwt_access_token_ttl_min * 60,
        **_COOKIE_BASE,
    )
    response.set_cookie(
        "refresh_token",
        refresh,
        max_age=settings.jwt_refresh_token_ttl_days * 86400,
        **_COOKIE_BASE,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> User:
    try:
        user = register_user(db, payload)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    _set_auth_cookies(response, user.id)
    return user


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    try:
        user = authenticate(db, payload.email, payload.password)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    _set_auth_cookies(response, user.id)
    return user


@router.post("/refresh", response_model=UserOut)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
) -> User:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no refresh token")
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired refresh token"
        ) from e

    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")

    _set_auth_cookies(response, user.id)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    _clear_auth_cookies(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
