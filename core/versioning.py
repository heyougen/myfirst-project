import re


VERSION_PATTERN = re.compile(r"^v\d+(?:\.\d+){0,3}(?:-[A-Za-z0-9._]+)?$")


def normalize_version(text: str) -> str:
    version = text.strip()
    if not version:
        return ""
    if version.startswith("V"):
        version = "v" + version[1:]
    if not version.startswith("v"):
        version = "v" + version
    return version


def is_valid_version(version: str) -> bool:
    return bool(VERSION_PATTERN.match(version))


def version_help() -> str:
    return "版本号格式建议：v1、v1.0、v1.0.1、v1.0-101"
