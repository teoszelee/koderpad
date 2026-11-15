from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from code_editor import code_editor

from utils import get_files


@dataclass
class ExecutionResult:
    text: str = ""
    error: str | None = None
    traceback: str = ""
    dataframe: pd.DataFrame | None = None
    success: str | None = None


@dataclass
class Workspace:
    exercise: str = ""
    revision: int = 0
    last_event_id: str = ""
    output: ExecutionResult | None = None

    def reset(self, exercise: str) -> None:
        self.exercise = exercise
        self.revision += 1
        self.last_event_id = ""
        self.output = None

    def consume_submit(self, response: dict[str, Any]) -> str | None:
        """Consume before executing, including empty submissions and failed runs."""
        event_id = response.get("id")
        if (
            response.get("type") != "submit"
            or not isinstance(event_id, str)
            or not event_id
            or event_id == self.last_event_id
        ):
            return None
        self.last_event_id = event_id
        text = response.get("text")
        return text if isinstance(text, str) and text.strip() else None


def render_editor(
    language: str, directory: Path, extension: str, settings: dict[str, Any]
) -> tuple[Workspace, str | None]:
    workspace_key = f"{language}_workspace"
    if workspace_key not in st.session_state:
        st.session_state[workspace_key] = Workspace()
    workspace: Workspace = st.session_state[workspace_key]

    with st.sidebar:
        try:
            files = get_files(directory, extension)
        except ValueError:
            files = []
        if not files:
            st.info("No exercises are available.")
            st.stop()
        selected = st.selectbox(
            "Load an exercise",
            files,
            format_func=lambda name: name.removesuffix(extension).title(),
            key=f"{language}_exercise",
            persist_state="session",
        )
        # Validate before constructing a path; options are a client-side guardrail.
        if not isinstance(selected, str) or selected not in files:
            st.error("Select an available exercise.")
            st.stop()
        if selected != workspace.exercise:
            workspace.reset(selected)
        if st.button(
            "Reset editor", key=f"{language}_reset", icon=":material/restart_alt:"
        ):
            workspace.reset(selected)

    try:
        source = (directory / selected).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        st.error("The selected exercise could not be read.")
        st.stop()

    response = code_editor(
        code=source,
        key=f"{language}_editor_{selected}_{workspace.revision}",
        **settings,
    )
    return workspace, workspace.consume_submit(response or {})


def show_output(result: ExecutionResult | None) -> None:
    if result is None:
        return
    st.subheader("Output")
    if result.error:
        st.error(result.error)
    if result.traceback:
        st.code(result.traceback, language="text", wrap_lines=True)
    if result.text:
        st.code(result.text, language="text", wrap_lines=True)
    if result.dataframe is not None:
        st.dataframe(
            result.dataframe,
            hide_index=True,
            width="stretch",
            alt="SQL query results",
        )
    if result.success:
        st.success(result.success)
