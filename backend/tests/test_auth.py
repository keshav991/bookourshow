import unittest
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.supabase import supabase_client
from app.dependencies.auth import get_current_user, require_role
from app.models.profile import Profile
from app.routes.users import get_my_profile, update_my_profile, get_my_bookings_demo
from app.schemas.auth import UserLoginRequest
from app.schemas.user import AuthenticatedUser, UserProfileUpdate
from app.services.auth_service import auth_service
from supabase_auth.errors import AuthApiError


class TestSupabaseAuthIntegration(unittest.TestCase):

    def test_01_settings_loaded(self):
        """1. Verify Supabase configuration loads successfully."""
        self.assertTrue(settings.SUPABASE_URL.startswith("https://"))
        self.assertTrue(len(settings.SUPABASE_PUBLISHABLE_KEY) > 10)
        self.assertIn("http://localhost:5173", settings.cors_origins_list)

    def test_02_supabase_client_initialized(self):
        """2. Verify Supabase Auth client initializes successfully."""
        self.assertIsNotNone(supabase_client)
        self.assertTrue(hasattr(supabase_client, "auth"))
        self.assertTrue(callable(supabase_client.auth.get_user))

    def test_03_missing_authorization_header(self):
        """3. Missing Authorization header is rejected with HTTP 401."""
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(None)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Missing Authorization header", ctx.exception.detail)

    def test_04_empty_token_rejected(self):
        """4. Empty Bearer token is rejected with HTTP 401."""
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials="   "))
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("token cannot be empty", ctx.exception.detail)

    def test_05_invalid_jwt_rejected(self):
        """5. Malformed/invalid JWT is rejected with HTTP 401."""
        with patch("app.dependencies.auth.supabase_client.auth.get_user", side_effect=AuthApiError("Invalid JWT", 401, None)):
            with self.assertRaises(HTTPException) as ctx:
                get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials="malformed.jwt.token"))
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Authentication failed", ctx.exception.detail)

    def test_06_profile_retrieval_success(self):
        """6. GET /users/me returns authenticated user's profile."""
        test_id = uuid.uuid4()
        auth_user = AuthenticatedUser(id=test_id, email="alice@example.com")
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = Profile(
            id=test_id,
            full_name="Alice Smith",
            role="customer"
        )

        response = get_my_profile(current_user=auth_user, db=mock_db)
        self.assertEqual(response.id, test_id)
        self.assertEqual(response.email, "alice@example.com")
        self.assertEqual(response.full_name, "Alice Smith")
        self.assertEqual(response.role, "customer")

    def test_07_profile_not_found_returns_404(self):
        """7. GET /users/me returns HTTP 404 when profile record is absent."""
        test_id = uuid.uuid4()
        auth_user = AuthenticatedUser(id=test_id, email="missing@example.com")
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            get_my_profile(current_user=auth_user, db=mock_db)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("User profile not found", ctx.exception.detail)

    def test_08_profile_update_preserves_role(self):
        """8. PUT /users/me updates full_name but keeps role strictly protected."""
        test_id = uuid.uuid4()
        auth_user = AuthenticatedUser(id=test_id, email="alice@example.com")
        mock_db = MagicMock()
        existing_profile = Profile(id=test_id, full_name="Alice Smith", role="customer")
        mock_db.query.return_value.filter.return_value.first.return_value = existing_profile

        payload = UserProfileUpdate(full_name="Alice Johnson")
        res = update_my_profile(payload=payload, current_user=auth_user, db=mock_db)
        self.assertEqual(res.full_name, "Alice Johnson")
        self.assertEqual(res.role, "customer")
        self.assertTrue(mock_db.commit.called)

    def test_09_rbac_forbidden_for_insufficient_role(self):
        """9. Role-based check forbids customer from accessing admin resource."""
        admin_gate = require_role("admin")
        test_id = uuid.uuid4()
        auth_user = AuthenticatedUser(id=test_id, email="user@example.com")
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = Profile(
            id=test_id,
            full_name="Regular User",
            role="customer"
        )

        with self.assertRaises(HTTPException) as ctx:
            admin_gate(current_user=auth_user, db=mock_db)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("insufficient role permissions", ctx.exception.detail)

    def test_10_rbac_allowed_for_matching_role(self):
        """10. Role-based check allows admin access."""
        admin_gate = require_role("admin")
        test_id = uuid.uuid4()
        auth_user = AuthenticatedUser(id=test_id, email="admin@example.com")
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = Profile(
            id=test_id,
            full_name="Super Admin",
            role="admin"
        )

        result = admin_gate(current_user=auth_user, db=mock_db)
        self.assertEqual(result.id, test_id)

    def test_11_booking_ownership_isolation(self):
        """11. Strict user data isolation ensures users only query their own data."""
        user_a_id = uuid.uuid4()
        user_a = AuthenticatedUser(id=user_a_id, email="user_a@example.com")
        mock_db = MagicMock()

        demo_res = get_my_bookings_demo(current_user=user_a, db=mock_db)
        self.assertEqual(demo_res["user_id"], str(user_a_id))
        self.assertIn("Booking.user_id == current_user.id", demo_res["message"])

    def test_12_auth_service_invalid_login(self):
        """12. Invalid credentials in login returns HTTP 401."""
        with patch("app.services.auth_service.supabase_client.auth.sign_in_with_password", side_effect=AuthApiError("Invalid login credentials", 401, None)):
            with self.assertRaises(HTTPException) as ctx:
                auth_service.login(UserLoginRequest(email="nonexistent@example.com", password="WrongPassword!"))
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Invalid email or password", ctx.exception.detail)

    def test_13_auth_service_logout(self):
        """13. Logout revokes token session cleanly."""
        with patch("app.services.auth_service.httpx.post") as post:
            post.return_value.is_error = False
            res = auth_service.logout(token="mock_or_test_token")
        self.assertIn("sign", res.message.lower())


if __name__ == "__main__":
    unittest.main()
