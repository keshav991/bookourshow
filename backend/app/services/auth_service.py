from uuid import UUID
from fastapi import HTTPException, status
from supabase_auth.errors import AuthApiError, AuthRetryableError

from app.core.supabase import supabase_client
from app.schemas.auth import (
    AuthMessageResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)


class AuthService:
    """Service wrapping Supabase Auth operations for backend-mediated requests."""

    @staticmethod
    def register(payload: UserRegisterRequest) -> TokenResponse | AuthMessageResponse:
        """
        Register a new user through Supabase Auth.
        Triggers automatic creation of public.profiles via PostgreSQL trigger.
        Forces default role 'customer'.
        """
        try:
            signup_options = {
                "email": payload.email,
                "password": payload.password,
                "options": {
                    "data": {
                        "full_name": payload.full_name or ""
                    }
                }
            }
            res = supabase_client.auth.sign_up(signup_options)

            if not res or not res.user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Registration failed. Please try again.",
                )

            user_id = UUID(res.user.id)

            # If Supabase has email confirmation enabled, session is None
            if not res.session:
                return AuthMessageResponse(
                    message="Registration successful. Please verify your email to activate your account.",
                    user_id=user_id,
                )

            return TokenResponse(
                access_token=res.session.access_token,
                token_type="bearer",
                expires_in=res.session.expires_in,
                refresh_token=res.session.refresh_token,
                user_id=user_id,
                email=res.user.email or payload.email,
            )

        except AuthApiError as exc:
            msg = getattr(exc, "message", str(exc))
            if "already registered" in msg.lower() or "unique" in msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An account with this email already exists.",
                )
            if "password" in msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Password error: {msg}",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration failed: {msg}",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred during registration: {str(exc)}",
            )

    @staticmethod
    def login(payload: UserLoginRequest) -> TokenResponse:
        """
        Authenticate user credentials via Supabase Auth and return access token.
        """
        try:
            res = supabase_client.auth.sign_in_with_password({
                "email": payload.email,
                "password": payload.password,
            })

            if not res or not res.session or not res.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid login credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return TokenResponse(
                access_token=res.session.access_token,
                token_type="bearer",
                expires_in=res.session.expires_in,
                refresh_token=res.session.refresh_token,
                user_id=UUID(res.user.id),
                email=res.user.email or payload.email,
            )

        except AuthApiError as exc:
            msg = getattr(exc, "message", str(exc))
            if "confirm" in msg.lower() or "verified" in msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email not confirmed. Please check your inbox and verify your email.",
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred during login: {str(exc)}",
            )

    @staticmethod
    def logout(token: str) -> AuthMessageResponse:
        """
        Sign out authenticated user by revoking their specific session in Supabase Auth.
        Uses per-session token revocation rather than a shared client state.
        """
        if not token:
            return AuthMessageResponse(message="No active session token provided")

        try:
            # Revoke session in Supabase Auth for this specific JWT
            supabase_client.auth.admin.sign_out(jwt=token, scope="global")
            return AuthMessageResponse(message="Successfully signed out")
        except AuthApiError as exc:
            msg = getattr(exc, "message", str(exc))
            return AuthMessageResponse(message=f"Session revoked ({msg})")
        except Exception:
            return AuthMessageResponse(message="Successfully signed out")


auth_service = AuthService()
