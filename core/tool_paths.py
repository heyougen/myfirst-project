import os


TOOL_DIR = ".stm32_git_tool"


def tool_dir(project_path: str) -> str:
    return os.path.join(project_path, TOOL_DIR)


def tool_file(project_path: str, *parts: str) -> str:
    return os.path.join(tool_dir(project_path), *parts)


def ensure_tool_dir(project_path: str) -> str:
    path = tool_dir(project_path)
    os.makedirs(path, exist_ok=True)
    return path
