import unittest
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies.auth import get_current_user
from app.schemas.auth import UserLoginRequest, UserRegisterRequest
from app.services.auth_service import auth_service
from supabase_auth.errors import AuthApiError


class TestEndToEndAuthFlow(unittest.TestCase):

    def test_missing_token_rejected(self):
        """Verify calling protected dependency without Bearer token returns 401."""
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(None)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Missing Authorization header", ctx.exception.detail)

    def test_invalid_jwt_signature_rejected(self):
        """Verify calling protected dependency with malformed/fake JWT returns 401."""
        with patch("app.dependencies.auth.supabase_client.auth.get_user", side_effect=AuthApiError("Invalid JWT", 401, None)):
            with self.assertRaises(HTTPException) as ctx:
                get_current_user(
                    HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake.jwt.token")
                )
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Authentication failed", ctx.exception.detail)

    def test_invalid_login_credentials(self):
        """Verify login with incorrect password returns 401."""
        with patch("app.services.auth_service.supabase_client.auth.sign_in_with_password", side_effect=AuthApiError("Invalid login credentials", 401, None)):
            with self.assertRaises(HTTPException) as ctx:
                auth_service.login(
                    UserLoginRequest(email="nonexistent.user@example.com", password="BadPassword999!")
                )
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Invalid email or password", ctx.exception.detail)

    def test_unconfirmed_email_login_rejected(self):
        """An unconfirmed test identity is rejected without contacting Supabase."""
        with patch("app.services.auth_service.supabase_client.auth.sign_in_with_password", side_effect=AuthApiError("Email not confirmed", 403, None)):
            with self.assertRaises(HTTPException) as ctx:
                auth_service.login(
                    UserLoginRequest(email="bookourshow.tester@example.com", password="Password123!")
                )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_logout_with_empty_token(self):
        """Verify logout without token indicates no active session."""
        res = auth_service.logout(token="")
        self.assertIn("no active session", res.message.lower())


if __name__ == "__main__":
    unittest.main()
