"""Session and project deletion module for CCSM.

This module handles all deletion operations including session deletion,
project deletion, and cleanup of orphaned data.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from ccsm.core.discovery import SessionDiscovery
from ccsm.core.models import DeleteResult, Session, SessionInfo


class SessionDeleter:
    """Handles deletion of Claude Code sessions and projects."""

    def __init__(self, claude_dir: Optional[Path] = None, dry_run: bool = False):
        """Initialize the deleter.

        Args:
            claude_dir: Path to Claude Code data directory. Defaults to ~/.claude/
            dry_run: If True, don't actually delete anything.
        """
        self.claude_dir = claude_dir or Path.home() / ".claude"
        self.dry_run = dry_run
        self.discovery = SessionDiscovery(self.claude_dir)

    def plan_session_deletion(self, session_id: str) -> SessionInfo:
        """Plan what files would be deleted for a session.

        Args:
            session_id: The session UUID to plan deletion for.

        Returns:
            SessionInfo with lists of files to delete.
        """
        session = self.discovery.get_session_by_id(session_id)
        if not session:
            return SessionInfo(session=Session(id=session_id))

        info = SessionInfo(session=session)
        session_id = session.id

        # Direct matches - files/dirs named with session_id
        direct_patterns = [
            ("tasks", self.claude_dir / "tasks" / session_id),
            ("todos", self.claude_dir / "todos" / f"*{session_id}*"),
            ("session-env", self.claude_dir / "session-env" / session_id),
            ("file-history", self.claude_dir / "file-history" / session_id),
            ("debug", self.claude_dir / "debug" / f"{session_id}.txt"),
        ]

        # Handle telemetry separately since it has a more complex pattern
        telemetry_dir = self.claude_dir / "telemetry"
        if telemetry_dir.exists():
            for tel_file in telemetry_dir.glob(f"1p_failed_events.{session_id}.*.json"):
                info.files_to_delete.append(str(tel_file))

        for pattern_name, pattern_path in direct_patterns:
            if "*" in str(pattern_path):
                # Glob pattern - use parent directory and glob the filename
                parent = pattern_path.parent
                pattern = pattern_path.name
                matches = list(parent.glob(pattern))
                for match in matches:
                    info.files_to_delete.append(str(match))
            else:
                # Direct path
                if pattern_path.exists():
                    info.files_to_delete.append(str(pattern_path))

        # Teams directory - team data for this session
        teams_dir = self.claude_dir / "teams" / session_id
        if teams_dir.exists():
            info.files_to_delete.append(str(teams_dir))

        # Sessions directory - session marker files (by PID)
        sessions_dir = self.claude_dir / "sessions"
        if sessions_dir.exists():
            for sess_file in sessions_dir.glob("*.json"):
                try:
                    with open(sess_file, "r", encoding="utf-8") as f:
                        sess_data = json.load(f)
                        if sess_data.get("sessionId") == session_id:
                            info.files_to_delete.append(str(sess_file))
                            break  # Only one match possible
                except (json.JSONDecodeError, IOError):
                    continue

        # Plans - Check if any plan files are associated with this session
        # First, get all plan references from history
        plan_refs = self._get_plan_references()
        for plan_path, ref_sessions in plan_refs.items():
            if len(ref_sessions) == 1 and session_id in ref_sessions:
                # Only this session references it - safe to delete
                info.files_to_delete.append(plan_path)
            elif len(ref_sessions) > 1:
                # Shared with other sessions
                # We don't add to shared list here (plans are handled differently)

                pass

 # Paste-cache - need to check reference count
        paste_hashes = self._get_session_paste_hashes(session_id)
        paste_refs = self.discovery.get_paste_hash_references()

        for content_hash in paste_hashes:
            refs = paste_refs.get(content_hash, set())
            if len(refs) == 1 and session_id in refs:
                # Only this session references it - safe to delete
                cache_file = self.claude_dir / "paste-cache" / f"{content_hash}.txt"
                if cache_file.exists():
                    info.paste_cache_to_delete.append(str(cache_file))
            elif len(refs) > 1:
                # Shared with other sessions
                cache_file = self.claude_dir / "paste-cache" / f"{content_hash}.txt"
                if cache_file.exists():
                    info.paste_cache_shared.append(str(cache_file))

        # History - will be modified (not deleted)
        history_file = self.claude_dir / "history.jsonl"
        if history_file.exists():
            info.files_to_modify.append(str(history_file))

        return info

    def _get_session_paste_hashes(self, session_id: str) -> list[str]:
        """Get contentHash values used by a specific session.

        Args:
            session_id: The session UUID.

        Returns:
            List of contentHash strings used by this session.
        """
        hashes = []
        history_path = self.claude_dir / "history.jsonl"

        if not history_path.exists():
            return hashes

        with open(history_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("sessionId") == session_id:
                        pasted_contents = entry.get("pastedContents", {})
                        for key, value in pasted_contents.items():
                            if isinstance(value, dict) and "contentHash" in value:
                                hashes.append(value["contentHash"])
                except json.JSONDecodeError:
                    continue

        return hashes

    def _get_plan_references(self) -> dict[str, set[str]]:
        """Get plan files and which sessions reference them.

        Returns:
            Dict mapping plan file path to set of session IDs that reference it.
        """
        from collections import defaultdict
        plan_refs = defaultdict(set)
        plans_dir = self.claude_dir / "plans"

        if not plans_dir.exists():
            return dict(plan_refs)

        # Get all plan files
        plan_files = set()
        for ext in ["*.md", "*.json"]:
            for pf in plans_dir.glob(ext):
                plan_files.add(str(pf))

        # Scan history for plan references
        history_path = self.claude_dir / "history.jsonl"
        if not history_path.exists():
            return dict(plan_refs)

        with open(history_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    session_id = entry.get("sessionId")
                    if not session_id:
                        continue
                    # Check display field for plan references
                    display = entry.get("display", "")
                    if isinstance(display, str):
                        for plan_file in plan_files:
                            plan_name = Path(plan_file).name
                            if plan_name in display:
                                plan_refs[plan_file].add(session_id)
                except json.JSONDecodeError:
                    continue

        return dict(plan_refs)

    def delete_session(self, session_id: str, force: bool = False) -> DeleteResult:
        """Delete a session and all its associated data.

        Args:
            session_id: The session UUID to delete.
            force: If True, skip confirmation for active sessions.

        Returns:
            DeleteResult with details of what was deleted.
        """
        result = DeleteResult(success=True)

        # Check if session exists
        session = self.discovery.get_session_by_id(session_id)
        if not session:
            result.success = False
            result.errors.append(f"Session '{session_id}' not found")
            return result

        # Check if session is active
        if session.status == "in_progress" and not force:
            result.errors.append(f"Session '{session_id}' is currently active. Use --force to delete anyway.")
            result.success = False
            return result

        # Get plan
        info = self.plan_session_deletion(session_id)

        # Add paste-cache shared files to files_to_delete (we delete them too after warning)
        all_files_to_delete = info.files_to_delete + info.paste_cache_to_delete

        # Delete files directly
        for file_path in all_files_to_delete:
            if self.dry_run:
                result.deleted_files.append(f"[DRY-RUN] Would delete: {file_path}")
                continue
            try:
                path = Path(file_path)
                if path.is_file():
                    os.remove(path)
                elif path.is_dir():
                    shutil.rmtree(path)
                result.deleted_files.append(file_path)
            except Exception as e:
                result.errors.append(f"Failed to delete {file_path}: {e}")

        # Handle paste-cache shared files
        if info.paste_cache_shared:
            result.skipped_files.extend(info.paste_cache_shared)

        # Handle history.jsonl
        history_path = self.claude_dir / "history.jsonl"
        if history_path.exists():
            if self.dry_run:
                result.modified_files.append("[DRY-RUN] Would rewrite: history.jsonl")
            else:
                try:
                    # Rewrite history.jsonl excluding this session
                    temp_fd, temp_path = tempfile.mkstemp(suffix=".jsonl", dir=self.claude_dir)
                    with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
                        with open(history_path, "r", encoding="utf-8") as orig_file:
                            for line in orig_file:
                                try:
                                    entry = json.loads(line.strip())
                                    if entry.get("sessionId") != session_id:
                                        temp_file.write(line)
                                except json.JSONDecodeError:
                                    # Preserve invalid/bad JSON lines to avoid data loss.
                                    temp_file.write(line)
                                    continue

                    # Replace original
                    shutil.move(temp_path, history_path)
                    result.modified_files.append(str(history_path))
                except Exception as e:
                    result.errors.append(f"Failed to update history.jsonl: {e}")

        return result

    def delete_project(self, project_path: str, include_claude_dir: bool = False, force: bool = False) -> DeleteResult:
        """Delete a project and all its associated sessions.

        Args:
            project_path: The project directory path.
            include_claude_dir: If True, also delete the project's .claude/ directory.
            force: If True, skip confirmation prompts.

        Returns:
            DeleteResult with details of what was deleted.
        """
        result = DeleteResult(success=True)

        # Find the project
        project = self.discovery.get_project_by_path(project_path)
        if not project:
            result.success = False
            result.errors.append(f"Project '{project_path}' not found")
            return result

        # Delete all sessions in the project
        for session in project.sessions:
            session_result = self.delete_session(session.id, force=force)
            result.deleted_files.extend(session_result.deleted_files)
            result.modified_files.extend(session_result.modified_files)
            result.errors.extend(session_result.errors)
            result.skipped_files.extend(session_result.skipped_files)
            if not session_result.success:
                result.success = False

        # Optionally delete the .claude/ directory in the project
        if include_claude_dir:
            claude_dir = Path(project_path) / ".claude"
            if claude_dir.exists():
                if self.dry_run:
                    result.deleted_files.append(f"[DRY-RUN] Would delete: {claude_dir}")
                else:
                    try:
                        shutil.rmtree(claude_dir)
                        result.deleted_files.append(str(claude_dir))
                    except Exception as e:
                        result.errors.append(f"Failed to delete {claude_dir}: {e}")

        return result

    def get_stale_history_entries(self) -> list[dict]:
        """Find entries in history.jsonl that reference non-existent sessions.

        Returns:
            List of dicts with 'line_number' and 'session_id' for stale entries.
        """
        stale = []
        history_path = self.claude_dir / "history.jsonl"

        if not history_path.exists():
            return stale

        # Get session IDs from projects/ directory only
        # Only sessions with .jsonl transcript files are considered "linked"
        projects_sessions = set()
        projects_dir = self.claude_dir / "projects"
        if projects_dir.exists():
            for proj_dir in projects_dir.iterdir():
                if proj_dir.is_dir() and proj_dir.name != ".DS_Store":
                    for f in proj_dir.glob("*.jsonl"):
                        sid = f.stem
                        if not sid.startswith("agent-"):
                            projects_sessions.add(sid)

        with open(history_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                try:
                    entry = json.loads(line.strip())
                    session_id = entry.get("sessionId")
                    # If session ID not in projects/ -> it's stale (not linked)
                    if session_id and session_id not in projects_sessions:
                        stale.append({
                            "line_number": line_num,
                            "session_id": session_id,
                            "project": entry.get("project"),
                            "timestamp": entry.get("timestamp"),
                        })
                except json.JSONDecodeError:
                    continue

        return stale

    def cleanup(self, auto_remove: bool = False) -> DeleteResult:
        """Clean up orphaned data and stale history entries.

        This automatically cleans:
        - Orphan sessions (sessions without projects)
        - Stale history.jsonl entries (sessions that no longer exist in data directories)

        Args:
            auto_remove: If True, automatically remove orphaned data.

        Returns:
            DeleteResult with details of cleanup.
        """
        result = DeleteResult(success=True)

        # Get orphan sessions
        orphans = self.discovery.get_orphan_sessions()

        # Always get stale history entries (clean them automatically)
        stale_entries = self.get_stale_history_entries()

        if not orphans and not stale_entries:
            result.skipped_files.append("No orphaned sessions or stale history entries found")
            return result

        if not auto_remove:
            # Just list what would be cleaned up
            for session in orphans:
                info = self.plan_session_deletion(session.id)
                result.skipped_files.append(f"Orphan session: {session.id} ({len(info.files_to_delete)} files)")

            for entry in stale_entries:
                result.skipped_files.append(
                    f"Stale history: line {entry['line_number']} - session {entry['session_id']} (project: {entry.get('project', 'N/A')})"
                )
            return result

        # CRITICAL: Clean stale history entries FIRST (before delete_session modifies history.jsonl)
        # If we delete sessions first, the line numbers become invalid
        if stale_entries:
            history_path = self.claude_dir / "history.jsonl"
            with open(history_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            stale_line_nums = {entry['line_number'] for entry in stale_entries}
            valid_lines = [line for i, line in enumerate(lines, start=1) if i not in stale_line_nums]

            with open(history_path, "w", encoding="utf-8") as f:
                f.writelines(valid_lines)

            result.modified_files.append(str(history_path))

        # Delete orphan sessions (history.jsonl already cleaned above)
        for session in orphans:
            session_result = self.delete_session(session.id)
            result.deleted_files.extend(session_result.deleted_files)
            result.modified_files.extend(session_result.modified_files)
            result.errors.extend(session_result.errors)

        return result