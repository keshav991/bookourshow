from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies.auth import get_current_user, security
from app.schemas.auth import (
    AuthMessageResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from app.schemas.user import AuthenticatedUser
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse | AuthMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers user in Supabase Auth. Triggers automated PostgreSQL profile creation with role 'customer'."
)
def register(payload: UserRegisterRequest):
    return auth_service.register(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login user",
    description="Authenticates credentials with Supabase Auth and returns an access JWT token."
)
def login(payload: UserLoginRequest):
    return auth_service.login(payload)


@router.post(
    "/logout",
    response_model=AuthMessageResponse,
    summary="Logout user",
    description="Revokes and terminates the authenticated user's session in Supabase Auth."
)
def logout(
    current_user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    token = credentials.credentials if credentials else ""
    return auth_service.logout(token=token)
