"""Core data discovery module for CCSM.

This module discovers sessions and projects from Claude Code's data directories.
"""

import json
import os
import glob
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from ccsm.core.models import Project, Session


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
            for plan_file in plans_dir.glob("*.json"):
                try:
                    with open(plan_file, "r", encoding="utf-8") as f:
                        plan_data = json.load(f)
                        session_id = plan_data.get("sessionId")
                        if session_id and session_id in sessions:
                            sessions[session_id].plan_count += 1
                except (json.JSONDecodeError, IOError):
                    continue

        # 8. Determine status and created_at from history
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
                    min_ts = min(timestamps)
                    sessions[session_id].created_at = datetime.fromtimestamp(min_ts / 1000)
                    # Assume most recent activity means still in_progress
                    sessions[session_id].status = "completed"

        # Check if any session is the current one
        current_session_id = os.environ.get("CLAUDE_SESSION_ID")
        if current_session_id and current_session_id in sessions:
            sessions[current_session_id].status = "in_progress"

        return list(sessions.values())

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

        # Build Project objects
        projects = []
        for path, proj_sessions in project_map.items():
            projects.append(Project(path=path, sessions=proj_sessions))

        # Sort by path
        projects.sort(key=lambda p: p.path)

        return projects

    def get_orphan_sessions(self) -> list[Session]:
        """Get sessions that don't have an associated project.

        Returns:
            List of orphan Session objects.
        """
        sessions = self.discover_all_sessions()
        session_to_project = self.session_to_project_map

        orphans = []
        for session in sessions:
            project_path = session.project_path or session_to_project.get(session.id)
            if not project_path:
                orphans.append(session)

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