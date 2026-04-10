"""Claude Code Session Manager - Manage and delete Claude Code sessions and projects."""

__version__ = "1.0.0"
__author__ = "You"

from ccsm.core.models import Project, Session, SessionInfo
from ccsm.core.discovery import SessionDiscovery
from ccsm.core.deleter import SessionDeleter

__all__ = [
    "Project",
    "Session",
    "SessionInfo",
    "SessionDiscovery",
    "SessionDeleter",
]