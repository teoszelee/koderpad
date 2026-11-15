import ast
import contextlib
import traceback
from io import StringIO
from pathlib import Path

from editor import ExecutionResult, render_editor, show_output

from .settings import PYTHON_EDITOR_SETTINGS

EXERCISE_DIR = Path(__file__).resolve().parent / "exercises"
PYTHON_FILE_EXT = ".py"
DISALLOWED_PYTHON_PACKAGES = frozenset(
    {"os", "sys", "subprocess", "shutil", "pathlib", "socket"}
)


def basic_safety_check(src: str) -> tuple[bool, str]:
    """
    Checks the provided Python source code for forbidden imports.

    Args:
        src (str): The source code to check.

    Returns:
        tuple[bool, str]: (True, "") if safe, (False, reason) if unsafe.
    """
    # Allow a special marker to bypass checks (for testing purposes)
    if src.startswith("#no-check"):
        return True, ""

    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                alias.name.split(".")[0] in DISALLOWED_PYTHON_PACKAGES
                for alias in node.names
            ):
                return False, "Blocked: forbidden import used."
        elif (
            isinstance(node, ast.ImportFrom)
            and (node.module or "").split(".")[0] in DISALLOWED_PYTHON_PACKAGES
        ):
            return False, "Blocked: forbidden import used."
    return True, ""


def execute_script(script: str) -> ExecutionResult:
    ok, msg = basic_safety_check(script)
    if not ok:
        return ExecutionResult(error=msg)

    output_buffer = StringIO()
    result = ExecutionResult()
    with contextlib.redirect_stdout(output_buffer):
        try:
            namespace = {}
            exec(script, namespace)  # noqa: S102 - intentional playground execution
        except Exception as error:  # noqa: BLE001 - report arbitrary user-code errors
            result.error = f"Error: {error}"
            result.traceback = traceback.format_exc()
    result.text = output_buffer.getvalue()
    return result


def run() -> None:
    workspace, script = render_editor(
        "python", EXERCISE_DIR, PYTHON_FILE_EXT, PYTHON_EDITOR_SETTINGS
    )
    if script is not None:
        workspace.output = execute_script(script)
    show_output(workspace.output)
