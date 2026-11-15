from pathlib import Path


def get_files(dir_path: Path, file_ext: str) -> list[str]:
    if not dir_path.is_dir():
        raise ValueError(f"The provided path '{dir_path}' is not a valid directory.")

    file_names = sorted(
        file.name for file in dir_path.glob(f"*{file_ext}") if file.is_file()
    )
    return file_names


# https://code-editor-documentation.streamlit.app/Advanced_usage#custom-buttons
RUN_BUTTON = {
    "name": "Run",
    "feather": "Play",
    "primary": True,
    "hasText": True,
    "showWithIcon": True,
    "commands": ["submit"],
    "alwaysOn": True,
    "style": {"bottom": "0.44rem", "right": "0.4rem"},
    "bindKey": {"win": "Ctrl-Enter", "mac": "Command-Enter"},
}
