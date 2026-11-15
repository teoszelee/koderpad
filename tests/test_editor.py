from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from editor import ExecutionResult, Workspace
from languages.python.executor import execute_script

APP = Path(__file__).parents[1] / "src/main.py"


@pytest.mark.parametrize(
    "response",
    [{}, {"type": "blur", "id": "1", "text": "x"}, {"type": "submit", "text": "x"}],
)
def test_non_submit_events_do_not_execute(response):
    assert Workspace().consume_submit(response) is None


def test_submit_is_consumed_once_even_when_empty():
    workspace = Workspace()
    event = {"type": "submit", "id": "one", "text": "print(1)"}
    assert workspace.consume_submit(event) == "print(1)"
    assert workspace.consume_submit(event) is None
    assert workspace.consume_submit({**event, "id": "two"}) == "print(1)"
    assert workspace.consume_submit({**event, "id": "three", "text": "  "}) is None
    assert workspace.last_event_id == "three"


def test_reset_clears_result_and_changes_editor_revision():
    workspace = Workspace(last_event_id="1", output=ExecutionResult(text="old"))
    workspace.reset("ex01.py")
    assert workspace.output is None
    assert workspace.last_event_id == ""
    assert workspace.revision == 1


def test_python_results_capture_output_and_errors():
    assert execute_script("print('hello')").text == "hello\n"
    result = execute_script("print('before'); raise ValueError('bad')")
    assert result.text == "before\n"
    assert result.error == "Error: bad"
    assert "ValueError: bad" in result.traceback
    assert "forbidden import" in (execute_script("import os").error or "")
    assert "Syntax error" in (execute_script("if").error or "")


def test_python_executes_once_and_preserves_output_across_reruns():
    event = {"type": "submit", "id": "one", "text": "print('saved')"}
    with (
        patch("auth.read_secrets", return_value={}),
        patch("editor.code_editor", return_value=event),
        patch(
            "languages.python.executor.execute_script", wraps=execute_script
        ) as execute,
    ):
        app = AppTest.from_file(str(APP)).run()
        assert not app.exception
        assert app.code[0].value == "saved"
        app.run()
        assert not app.exception
        assert app.code[0].value == "saved"
        assert execute.call_count == 1


def test_failed_python_submission_is_not_retried():
    event = {"type": "submit", "id": "one", "text": "raise ValueError('bad')"}
    with (
        patch("auth.read_secrets", return_value={}),
        patch("editor.code_editor", return_value=event),
        patch(
            "languages.python.executor.execute_script", wraps=execute_script
        ) as execute,
    ):
        app = AppTest.from_file(str(APP)).run()
        app.run()
        assert not app.exception
        assert app.error[0].value == "Error: bad"
        assert execute.call_count == 1


def test_exercise_switch_and_reset_clear_output_and_remount_editor():
    with (
        patch("auth.read_secrets", return_value={}),
        patch("editor.code_editor", return_value={}) as editor,
    ):
        app = AppTest.from_file(str(APP)).run()
        initial_key = editor.call_args.kwargs["key"]
        app.session_state["python_workspace"].output = ExecutionResult(text="old")
        app.selectbox(key="python_exercise").select("ex01.py").run()
        assert not app.exception
        assert not app.code
        switched_key = editor.call_args.kwargs["key"]
        assert initial_key != switched_key
        app.button(key="python_reset").click().run()
        assert not app.exception
        assert switched_key != editor.call_args.kwargs["key"]


def test_page_switch_preserves_exercise_and_never_loads_database():
    with (
        patch("auth.read_secrets", return_value={}),
        patch("editor.code_editor", return_value={}) as editor,
        patch(
            "streamlit.connection", side_effect=AssertionError("Unexpected DB access")
        ),
    ):
        app = AppTest.from_file(str(APP)).run()
        app.selectbox(key="python_exercise").select("ex02.py").run()
        app.switch_page("app_pages/dockerfile.py").run()
        assert not app.exception
        assert app.selectbox(key="dockerfile_exercise")
        assert editor.call_args.kwargs["lang"] == "dockerfile"
        app.switch_page("app_pages/python.py").run()
        assert not app.exception
        assert app.selectbox(key="python_exercise").value == "ex02.py"


def test_empty_exercise_directory_is_handled(tmp_path):
    with (
        patch("auth.read_secrets", return_value={}),
        patch("languages.python.executor.EXERCISE_DIR", tmp_path),
        patch("editor.code_editor") as editor,
    ):
        app = AppTest.from_file(str(APP)).run()
        assert not app.exception
        assert app.info[0].value == "No exercises are available."
        editor.assert_not_called()
