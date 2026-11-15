from collections.abc import Mapping
from typing import Any

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


def read_secrets() -> dict[str, Any]:
    """Missing secrets are supported for local, non-SQL development."""
    try:
        return st.secrets.to_dict()
    except StreamlitSecretNotFoundError as error:
        if error.error_id == "no-secrets-found":
            return {}
        # Streamlit uses the same exception for invalid TOML and missing files.
        # A broken auth configuration must not turn sign-in off.
        raise


def auth_config_error(secrets: Mapping[str, Any]) -> str | None:
    if "APP_PWD" in secrets:
        return "APP_PWD is no longer supported. Remove it and configure OIDC in [auth]."
    if "auth" not in secrets:
        return None
    config = secrets["auth"]
    required = (
        "redirect_uri",
        "cookie_secret",
        "client_id",
        "client_secret",
        "server_metadata_url",
    )
    if not isinstance(config, Mapping) or any(
        not isinstance(config.get(key), str) or not config[key].strip()
        for key in required
    ):
        return "Complete [auth] with redirect_uri, cookie_secret, client_id, client_secret, and server_metadata_url."
    return None


def require_sign_in() -> None:
    try:
        secrets = read_secrets()
    except (StreamlitSecretNotFoundError, OSError):
        st.error(
            "The secrets configuration could not be loaded. Check .streamlit/secrets.toml.",
            title="Authentication configuration required",
        )
        st.stop()
    error = auth_config_error(secrets)
    if error:
        st.error(error, title="Authentication configuration required")
        st.stop()
    if "auth" not in secrets:
        return
    if not st.user.is_logged_in:
        st.title("Sign in to Koderpad")
        if st.button("Sign in", icon=":material/login:", key="sign_in"):
            st.login()
        st.stop()
    with st.sidebar:
        st.caption(
            f"Signed in as {st.user.get('email') or st.user.get('name') or 'user'}"
        )
        if st.button("Sign out", icon=":material/logout:", key="sign_out"):
            st.logout()
            st.stop()
