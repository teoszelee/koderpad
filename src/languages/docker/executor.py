from pathlib import Path

from editor import render_editor

from .settings import DOCKERFILE_EDITOR_SETTINGS

EXERCISE_DIR = Path(__file__).resolve().parent / "exercises"
DOCKERFILE_EXT = ".Dockerfile"


def run() -> None:
    render_editor(
        "dockerfile", EXERCISE_DIR, DOCKERFILE_EXT, DOCKERFILE_EDITOR_SETTINGS
    )
