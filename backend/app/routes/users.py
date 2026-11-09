from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.profile import Profile
from app.schemas.user import AuthenticatedUser, UserProfileResponse, UserProfileUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description="Validates Supabase JWT and fetches profile from PostgreSQL public.profiles."
)
def get_my_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve profile from PostgreSQL using the cryptographically verified user ID.
    Returns HTTP 404 if the profile record does not exist.
    """
    profile = db.query(Profile).filter(Profile.id == current_user.id).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found in database. Ensure the PostgreSQL signup trigger is configured.",
        )

    return UserProfileResponse(
        id=profile.id,
        email=current_user.email,
        full_name=profile.full_name,
        role=profile.role,
    )


@router.put(
    "/me",
    response_model=UserProfileResponse,
    summary="Update current user profile",
    description="Updates user profile fields (e.g. full_name). Strictly forbids updating user role."
)
def update_my_profile(
    payload: UserProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Updates the current user's profile information.
    Role is strictly immutable through this endpoint to prevent privilege escalation.
    """
    profile = db.query(Profile).filter(Profile.id == current_user.id).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found in database.",
        )

    profile.full_name = payload.full_name.strip()
    db.commit()
    db.refresh(profile)

    return UserProfileResponse(
        id=profile.id,
        email=current_user.email,
        full_name=profile.full_name,
        role=profile.role,
    )


@router.get(
    "/me/bookings-demo",
    summary="Demonstration: Ownership-Enforced User Bookings",
    description="Demonstrates how future booking APIs enforce strict user data isolation using get_current_user."
)
def get_my_bookings_demo(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Architectural demonstration:
    Queries are strictly filtered by current_user.id (from the verified JWT),
    preventing any user from accessing another user's reservation records.
    Example future query:
        db.query(Booking).filter(Booking.user_id == current_user.id).all()
    """
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "message": "Ownership strictly enforced. Future queries will filter by: Booking.user_id == current_user.id",
        "bookings": []
    }
