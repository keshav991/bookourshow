from typing import List, Union
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from supabase_auth.errors import AuthApiError, AuthInvalidJwtError

from app.core.supabase import supabase_client
from app.database import get_db
from app.models.profile import Profile
from app.schemas.user import AuthenticatedUser

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthenticatedUser:
    """
    Extract and verify the Supabase JWT token from the Authorization header.
    Validates token authenticity, signature, expiry, issuer, and audience
    via Supabase Auth API without blindly trusting client claims.

    Raises HTTP 401 Unauthorized for missing, malformed, or expired tokens.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header or invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token cannot be empty",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Cryptographically verifies signature, expiry, and returns authenticated user
        response = supabase_client.auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = response.user
        return AuthenticatedUser(
            id=UUID(user.id),
            email=user.email,
            user_metadata=user.user_metadata or {},
            app_metadata=user.app_metadata or {},
        )

    except (AuthApiError, AuthInvalidJwtError) as exc:
        message = getattr(exc, "message", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {message}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(allowed_roles: Union[List[str], str]):
    """
    Role-based access control (RBAC) dependency factory.
    Verifies the user's role against the trusted PostgreSQL public.profiles record.
    Never trusts client-supplied roles.
    """
    roles_list = [allowed_roles] if isinstance(allowed_roles, str) else allowed_roles

    def role_verifier(
        current_user: AuthenticatedUser = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> AuthenticatedUser:
        profile = db.query(Profile).filter(Profile.id == current_user.id).first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile record not found in database",
            )
        if profile.role not in roles_list:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: insufficient role permissions",
            )
        return current_user

    return role_verifier
