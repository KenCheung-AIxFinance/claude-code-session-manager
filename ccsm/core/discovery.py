"""Core data discovery module for CCSM.

This module discovers sessions and projects from Claude Code's data directories.
"""

import json
import os
import re
import glob
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from ccsm.core.models import Project, Session


# Wrappers Claude Code injects into the user-message stream. We strip these
# before falling back to "first user message" as a session title.
_NOISE_TAGS = (
    "local-command-caveat",
    "command-message",
    "command-name",
    "command-args",
    "command-stdout",
    "command-stderr",
    "system-reminder",
    "bash-input",
    "bash-stdout",
    "bash-stderr",
    "user-prompt-submit-hook",
)
_NOISE_RE = re.compile(
    "|".join(rf"<{tag}>.*?</{tag}>" for tag in _NOISE_TAGS), re.DOTALL
)


class SessionDiscovery:
    """Discovers Claude Code sessions and projects."""

    def __init__(self, claude_dir: Optional[Path] = None):
        """Initialize the discovery engine.

        Args:
            claude_dir: Path to Claude Code data directory. Defaults to ~/.claude/
        """
        self.claude_dir = claude_dir or Path.home() / ".claude"
        self._session_to_project_cache: Optional[dict[str, str]] = None
        self._paste_hash_references: Optional[dict[str, set[str]]] = None

    @property
    def session_to_project_map(self) -> dict[str, str]:
        """Build a map of session_id -> project_path from history.jsonl."""
        if self._session_to_project_cache is not None:
            return self._session_to_project_cache

        self._session_to_project_cache = {}
        history_path = self.claude_dir / "history.jsonl"

        if not history_path.exists():
            return {}

        with open(history_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    session_id = entry.get("sessionId")
                    project = entry.get("project")
                    if session_id and project:
                        # Store unique mapping (first one wins)
                        if session_id not in self._session_to_project_cache:
                            self._session_to_project_cache[session_id] = project
                except json.JSONDecodeError:
                    continue

        return self._session_to_project_cache

    def invalidate_cache(self) -> None:
        """Invalidate all caches to force refresh on next access.

        This should be called after deletion operations to ensure
        stale data is not displayed.
        """
        self._session_to_project_cache = None
        self._paste_hash_references = None

    def get_paste_hash_references(self) -> dict[str, set[str]]:
        """Build a map of contentHash -> set of session_ids that reference it.

        This is used to determine if a paste-cache file can be safely deleted
        when removing a session (only if no other sessions reference it).
        """
        if self._paste_hash_references is not None:
            return self._paste_hash_references

        self._paste_hash_references = defaultdict(set)
        history_path = self.claude_dir / "history.jsonl"

        if not history_path.exists():
            return dict(self._paste_hash_references)

        with open(history_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    session_id = entry.get("sessionId")
                    pasted_contents = entry.get("pastedContents", {})

                    if session_id and pasted_contents:
                        for key, value in pasted_contents.items():
                            if isinstance(value, dict) and "contentHash" in value:
                                content_hash = value["contentHash"]
                                self._paste_hash_references[content_hash].add(session_id)
                except json.JSONDecodeError:
                    continue

        return dict(self._paste_hash_references)

    def discover_all_sessions(self) -> list[Session]:
        """Discover all sessions from Claude Code data directories.

        Returns:
            List of Session objects with basic metadata.
        """
        sessions = {}
        session_to_project = self.session_to_project_map

        # 1. Discover from tasks/ directories
        tasks_dir = self.claude_dir / "tasks"
        if tasks_dir.exists():
            for session_dir in tasks_dir.iterdir():
                if session_dir.is_dir() and session_dir.name != ".DS_Store":
                    session_id = session_dir.name
                    sessions[session_id] = Session(
                        id=session_id,
                        project_path=session_to_project.get(session_id),
                        task_count=len([f for f in session_dir.iterdir() if f.name.endswith(".json")]),
                    )

        # 2. Discover from todos/
        todos_dir = self.claude_dir / "todos"
        if todos_dir.exists():
            for todo_file in todos_dir.glob("*.json"):
                # Format: {session_id}-agent-{session_id}.json
                name = todo_file.stem
                # Handle the case where filename has the agent- prefix
                if "-agent-" in name:
                    parts = name.split("-agent-")
                    if len(parts) == 2:
                        session_id = parts[0]
                        if session_id in sessions:
                            sessions[session_id].todo_count += 1

        # 3. Discover from session-env/
        session_env_dir = self.claude_dir / "session-env"
        if session_env_dir.exists():
            for env_dir in session_env_dir.iterdir():
                if env_dir.is_dir() and env_dir.name != ".DS_Store":
                    session_id = env_dir.name
                    if session_id not in sessions:
                        sessions[session_id] = Session(
                            id=session_id,
                            project_path=session_to_project.get(session_id),
                        )

        # 4. Discover from file-history/
        file_history_dir = self.claude_dir / "file-history"
        if file_history_dir.exists():
            for hist_dir in file_history_dir.iterdir():
                if hist_dir.is_dir() and hist_dir.name != ".DS_Store":
                    session_id = hist_dir.name
                    if session_id not in sessions:
                        sessions[session_id] = Session(
                            id=session_id,
                            project_path=session_to_project.get(session_id),
                        )

        # 5. Discover from debug/
        debug_dir = self.claude_dir / "debug"
        if debug_dir.exists():
            for debug_file in debug_dir.glob("*.txt"):
                session_id = debug_file.stem
                if session_id not in sessions:
                    sessions[session_id] = Session(
                        id=session_id,
                        project_path=session_to_project.get(session_id),
                    )

        # 6. Discover from telemetry/
        telemetry_dir = self.claude_dir / "telemetry"
        if telemetry_dir.exists():
            # Format: 1p_failed_events.{session_id}.{event_id}.json
            for tel_file in telemetry_dir.glob("1p_failed_events.*.json"):
                name = tel_file.name
                # Extract session_id from filename
                parts = name.split(".")
                if len(parts) >= 3:
                    session_id = parts[1]
                    if session_id not in sessions:
                        sessions[session_id] = Session(
                            id=session_id,
                            project_path=session_to_project.get(session_id),
                        )

        # 7. Discover from plans/
        plans_dir = self.claude_dir / "plans"
        if plans_dir.exists():
            for plan_file in plans_dir.glob("*.md"):
                try:
                    with open(plan_file, "r", encoding="utf-8") as f:
                        plan_data = json.load(f)
                        session_id = plan_data.get("sessionId")
                        if session_id and session_id in sessions:
                            sessions[session_id].plan_count += 1
                except (json.JSONDecodeError, IOError):
                    continue

            # 8. Discover from projects/ directories
        # These contain .jsonl transcript files for sessions
        session_transcripts: dict[str, Path] = {}
        projects_dir = self.claude_dir / "projects"
        if projects_dir.exists():
            for proj_dir in projects_dir.iterdir():
                if proj_dir.is_dir() and proj_dir.name != ".DS_Store":
                    for session_file in proj_dir.glob("*.jsonl"):
                        session_id = session_file.stem
                        # Skip agent-* files (these are internal agent sessions)
                        if session_id.startswith("agent-"):
                            continue
                        session_transcripts[session_id] = session_file
                        if session_id not in sessions:
                            sessions[session_id] = Session(
                                id=session_id,
                                project_path=session_to_project.get(session_id),
                                has_transcript=True,
                            )
                        else:
                            sessions[session_id].has_transcript = True

    # 9. Determine status and created_at from history
        history_path = self.claude_dir / "history.jsonl"
        if history_path.exists():
            session_times = defaultdict(list)
            with open(history_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        session_id = entry.get("sessionId")
                        timestamp = entry.get("timestamp")
                        if session_id and timestamp and session_id in sessions:
                            session_times[session_id].append(timestamp)
                    except json.JSONDecodeError:
                        continue

            for session_id, timestamps in session_times.items():
                if timestamps:
                    sessions[session_id].created_at = datetime.fromtimestamp(min(timestamps) / 1000)
                    sessions[session_id].updated_at = datetime.fromtimestamp(max(timestamps) / 1000)
                    # Assume most recent activity means still in_progress
                    sessions[session_id].status = "completed"

        # Prefer transcript file mtime as updated_at — it captures assistant
        # writes too, not just user prompts in history.jsonl.
        for session_id, transcript in session_transcripts.items():
            if session_id not in sessions:
                continue
            try:
                mtime = transcript.stat().st_mtime
            except OSError:
                continue
            ts = datetime.fromtimestamp(mtime)
            current = sessions[session_id].updated_at
            if current is None or ts > current:
                sessions[session_id].updated_at = ts

        # Check if any session is the current one
        current_session_id = os.environ.get("CLAUDE_SESSION_ID")
        if current_session_id and current_session_id in sessions:
            sessions[current_session_id].status = "in_progress"

        # 10. Populate session names. Priority: live PID marker (reflects a
        # rename before it lands in the transcript) > last custom-title in
        # the transcript > first non-boilerplate user prompt.
        live_names = self._live_session_names()
        for session_id, session in sessions.items():
            name = live_names.get(session_id)
            if not name:
                transcript = session_transcripts.get(session_id)
                if transcript is not None:
                    title, first_prompt = self._read_transcript_metadata(transcript)
                    name = title or first_prompt
            if name:
                session.name = name

        return list(sessions.values())

    def _live_session_names(self) -> dict[str, str]:
        """Map sessionId -> name from live PID marker files in sessions/."""
        result: dict[str, str] = {}
        sessions_dir = self.claude_dir / "sessions"
        if not sessions_dir.exists():
            return result
        for marker in sessions_dir.glob("*.json"):
            try:
                with open(marker, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError, OSError):
                continue
            session_id = data.get("sessionId")
            name = data.get("name")
            if session_id and isinstance(name, str) and name.strip():
                result[session_id] = name.strip()
        return result

    @staticmethod
    def _read_transcript_metadata(path: Path) -> tuple[Optional[str], Optional[str]]:
        """Return (last_custom_title, first_user_prompt) from a transcript.

        Single forward pass. The first-user-prompt search short-circuits as
        soon as a non-empty cleaned prompt is found; the custom-title search
        keeps overwriting because the LAST entry wins.
        """
        last_title: Optional[str] = None
        first_prompt: Optional[str] = None
        try:
            with open(path, "rb") as f:
                for raw in f:
                    if b'"custom-title"' in raw:
                        try:
                            entry = json.loads(raw)
                        except json.JSONDecodeError:
                            entry = None
                        if entry and entry.get("type") == "custom-title":
                            title = entry.get("customTitle")
                            if isinstance(title, str) and title.strip():
                                last_title = title.strip()
                        continue
                    if first_prompt is None and b'"type":"user"' in raw:
                        try:
                            entry = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        if entry.get("type") != "user" or entry.get("isSidechain"):
                            continue
                        text = SessionDiscovery._extract_user_text(
                            entry.get("message", {})
                        )
                        cleaned = SessionDiscovery._clean_user_text(text)
                        if cleaned:
                            first_prompt = cleaned
        except (IOError, OSError):
            pass
        return last_title, first_prompt

    @staticmethod
    def _extract_user_text(message: dict) -> str:
        """Pull plain text out of a user message (string or content blocks)."""
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
            return "\n".join(parts)
        return ""

    @staticmethod
    def _clean_user_text(text: str) -> str:
        """Strip Claude Code's injected wrappers and shorten to one title-like line.

        Returns "" for entries that are unlikely to be meaningful titles —
        short single-word prompts ("clear", "Continue", "Yes") that are
        usually slash-command echoes or follow-up confirmations.
        """
        text = _NOISE_RE.sub("", text)
        text = text.strip()
        if not text:
            return ""
        # Take the first paragraph so a long prompt doesn't bleed into the title.
        first_para = text.split("\n\n", 1)[0]
        # Collapse internal whitespace to keep it on one line.
        first_para = re.sub(r"\s+", " ", first_para).strip()
        # Skip single short words — almost always slash-command echoes or "yes"/"continue".
        if len(first_para) < 15 and " " not in first_para:
            return ""
        if len(first_para) > 100:
            first_para = first_para[:97].rstrip() + "..."
        return first_para

    def discover_projects(self) -> list[Project]:
        """Discover all projects and their associated sessions.

        Returns:
            List of Project objects with nested sessions.
        """
        sessions = self.discover_all_sessions()
        session_to_project = self.session_to_project_map

        # Group sessions by project
        project_map: dict[str, list[Session]] = defaultdict(list)

        for session in sessions:
            project_path = session.project_path or session_to_project.get(session.id)
            if project_path:
                project_map[project_path].append(session)
            else:
                # Sessions without a project go to a special "None" bucket
                # But we'll handle them separately
                pass

        # Build Project objects with sessions sorted by most recent activity.
        projects = []
        for path, proj_sessions in project_map.items():
            proj_sessions.sort(key=self._session_sort_key, reverse=True)
            projects.append(Project(path=path, sessions=proj_sessions))

        # Sort by path
        projects.sort(key=lambda p: p.path)

        return projects

    @staticmethod
    def _session_sort_key(session: Session):
        """Sort by updated_at desc, fall back to created_at, then session id."""
        ts = session.updated_at or session.created_at
        # datetime.min keeps untimestamped sessions at the bottom when reversed.
        return (ts or datetime.min, session.id)

    def get_projects_session_ids(self) -> set[str]:
        """Get all session IDs that have .jsonl files in projects/.

        Returns:
            Set of session IDs that are linked to projects (have transcripts).
        """
        projects_sessions = set()
        projects_dir = self.claude_dir / "projects"
        if projects_dir.exists():
            for proj_dir in projects_dir.iterdir():
                if proj_dir.is_dir() and proj_dir.name != ".DS_Store":
                    for session_file in proj_dir.glob("*.jsonl"):
                        session_id = session_file.stem
                        # Skip agent-* files (internal agent sessions)
                        if not session_id.startswith("agent-"):
                            projects_sessions.add(session_id)
        return projects_sessions

    def get_orphan_sessions(self) -> list[Session]:
        """Get sessions that don't have a corresponding .jsonl file in projects/.

        An orphan session is one that exists in data directories (tasks/, todos/, etc.)
        but has no transcript file in projects/.

        Returns:
            List of orphan Session objects.
        """
        sessions = self.discover_all_sessions()
        projects_session_ids = self.get_projects_session_ids()

        orphans = []
        for session in sessions:
            # Sessions without transcripts are orphans.
            # Sessions with transcripts but no project mapping are also surfaced
            # so transcript-only leftovers do not become invisible.
            if session.id not in projects_session_ids or (session.has_transcript and not session.project_path):
                orphans.append(session)

        orphans.sort(key=self._session_sort_key, reverse=True)
        return orphans

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """Get a specific session by its ID.

        Args:
            session_id: The session UUID.

        Returns:
            Session object if found, None otherwise.
        """
        sessions = self.discover_all_sessions()
        for session in sessions:
            if session.id == session_id:
                return session
        return None

    def get_project_by_path(self, project_path: str) -> Optional[Project]:
        """Get a specific project by its path.

        Args:
            project_path: The project directory path.

        Returns:
            Project object if found, None otherwise.
        """
        # Normalize the input path: expand ~ and remove trailing slashes
        normalized_input = os.path.normpath(os.path.expanduser(project_path))

        projects = self.discover_projects()
        for project in projects:
            # Normalize the stored path the same way before comparing
            normalized_stored = os.path.normpath(os.path.expanduser(project.path))
            if normalized_stored == normalized_input:
                return project
        return None