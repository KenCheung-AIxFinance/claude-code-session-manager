"""Data models for CCSM."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Session:
    """Represents a Claude Code session."""

    id: str
    project_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: str = "unknown"  # in_progress, completed, unknown
    task_count: int = 0
    todo_count: int = 0
    plan_count: int = 0
    has_transcript: bool = False
    name: Optional[str] = None  # User-set or auto-generated session title

    def __str__(self) -> str:
        return f"Session({self.id[:8]}...)"


@dataclass
class Project:
    """Represents a Claude Code project."""

    path: str
    sessions: list[Session] = field(default_factory=list)

    @property
    def session_count(self) -> int:
        return len(self.sessions)

    def __str__(self) -> str:
        return f"Project({self.path}, {self.session_count} sessions)"


@dataclass
class SessionInfo:
    """Detailed information about a session for deletion planning."""

    session: Session
    files_to_delete: list[str] = field(default_factory=list)
    files_to_modify: list[str] = field(default_factory=list)
    paste_cache_to_delete: list[str] = field(default_factory=list)
    paste_cache_shared: list[str] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        return len(self.files_to_delete)


@dataclass
class DeleteResult:
    """Result of a delete operation."""

    success: bool
    deleted_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)

    @property
    def total_deleted(self) -> int:
        # De-duplicate because project deletion aggregates per-session results,
        # and history.jsonl may be rewritten once per session.
        return len(set(self.deleted_files))

    @property
    def total_modified(self) -> int:
        return len(set(self.modified_files))

    @property
    def total_errors(self) -> int:
        return len(self.errors)