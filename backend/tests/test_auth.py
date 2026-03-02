from app.auth import clear_sessions, get_user, login, logout


class TestAuth:
    def setup_method(self):
        clear_sessions()

    def test_login_with_valid_credentials(self):
        token = login("user", "password")
        assert token is not None
        assert len(token) == 32  # hex UUID

    def test_login_with_wrong_password(self):
        assert login("user", "wrong") is None

    def test_login_with_wrong_username(self):
        assert login("admin", "password") is None

    def test_get_user_with_valid_token(self):
        token = login("user", "password")
        assert get_user(token) == "user"

    def test_get_user_with_invalid_token(self):
        assert get_user("nonexistent") is None

    def test_logout_invalidates_token(self):
        token = login("user", "password")
        assert logout(token) is True
        assert get_user(token) is None

    def test_logout_unknown_token(self):
        assert logout("nonexistent") is False
