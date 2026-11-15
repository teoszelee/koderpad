from unittest.mock import Mock, patch

import pytest
from streamlit.errors import StreamlitSecretNotFoundError
from streamlit.testing.v1 import AppTest
from test_editor import APP

from auth import auth_config_error, read_secrets

AUTH = {
    "redirect_uri": "http://localhost:8501/oauth2callback",
    "cookie_secret": "test-cookie-secret",
    "client_id": "test-client",
    "client_secret": "test-secret",
    "server_metadata_url": "https://example.com/.well-known/openid-configuration",
}


def test_missing_secrets_support_local_development():
    with patch(
        "streamlit.secrets",
        Mock(
            to_dict=Mock(
                side_effect=StreamlitSecretNotFoundError(
                    "missing", error_id="no-secrets-found"
                )
            )
        ),
    ):
        assert read_secrets() == {}
    assert auth_config_error({}) is None


def test_malformed_secrets_do_not_disable_authentication():
    error = StreamlitSecretNotFoundError(
        "parse failed", error_id="failed-parsing-secrets-file"
    )
    with (
        patch("streamlit.secrets", Mock(to_dict=Mock(side_effect=error))),
        pytest.raises(StreamlitSecretNotFoundError),
    ):
        read_secrets()
    with (
        patch("auth.read_secrets", side_effect=error),
        patch("editor.code_editor") as editor,
    ):
        app = AppTest.from_file(str(APP)).run()
        assert not app.exception
        assert app.error
        editor.assert_not_called()


@pytest.mark.parametrize(
    "secrets",
    [
        {"APP_PWD": "legacy"},
        {"auth": {}},
        {"auth": "bad"},
        {"auth": {**AUTH, "client_id": " "}},
    ],
)
def test_invalid_auth_blocks_pages(secrets):
    with (
        patch("auth.read_secrets", return_value=secrets),
        patch("editor.code_editor") as editor,
    ):
        app = AppTest.from_file(str(APP)).run()
        assert not app.exception
        assert app.error
        assert not app.selectbox
        editor.assert_not_called()


def test_login_gate_and_login_action():
    with (
        patch("auth.read_secrets", return_value={"auth": AUTH}),
        patch("streamlit.login") as login,
        patch("editor.code_editor") as editor,
    ):
        app = AppTest.from_file(str(APP))
        app.user = {"is_logged_in": False}
        app.run()
        assert not app.exception
        editor.assert_not_called()
        app.button(key="sign_in").click().run()
        login.assert_called_once_with()


def test_authenticated_user_can_access_pages_and_logout():
    with (
        patch("auth.read_secrets", return_value={"auth": AUTH}),
        patch("streamlit.logout") as logout,
        patch("editor.code_editor", return_value={}),
    ):
        app = AppTest.from_file(str(APP))
        app.user = {"is_logged_in": True, "email": "anyone@example.com"}
        app.run()
        assert not app.exception
        assert app.selectbox(key="python_exercise")
        app.button(key="sign_out").click().run()
        assert not app.exception
        logout.assert_called_once_with()
