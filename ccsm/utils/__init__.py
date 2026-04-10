"""Utilities module for CCSM."""

from pathlib import Path
from typing import Optional


def get_claude_dir() -> Path:
    """Get the Claude Code data directory.

    Returns:
        Path to ~/.claude/
    """
    return Path.home() / ".claude"


def expand_path(path: str) -> Path:
    """Expand a path with ~ expansion.

    Args:
        path: Path string that may contain ~

    Returns:
        Expanded Path object.
    """
    return Path(path).expanduser()


def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID.

    Args:
        value: String to check.

    Returns:
        True if valid UUID format.
    """
    import re
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    return bool(uuid_pattern.match(value))