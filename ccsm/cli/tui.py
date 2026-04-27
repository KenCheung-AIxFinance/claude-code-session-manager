"""Textual TUI for CCSM - Human-friendly interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, Static
from textual import on

from ccsm.core import SessionDeleter, SessionDiscovery
from ccsm.core.models import Project, Session


@dataclass
class ViewState:
    mode: str = "projects"  # "projects" | "orphans"
    selected_project_index: Optional[int] = None
    selected_session_index: Optional[int] = None


class CCSMApp(App):
    """Claude Code Session Manager Textual TUI - Human-friendly."""

    CSS = """
    Screen { background: $surface; }

    #header-bar {
        height: auto;
        background: $primary;
        padding: 0 1;
    }

    #main-area {
        height: 1fr;
        layout: horizontal;
    }

    #left-panel {
        width: 50;
        border: solid $primary;
        padding: 0 1;
    }

    #right-panel {
        width: 1fr;
        border: solid $secondary;
        padding: 0 1;
    }

    #detail-panel {
        width: 45;
        border: solid $accent;
        padding: 0 1;
    }

    .section-title {
        text-style: bold;
        color: $text;
        margin: 1 0;
    }

    .hint {
        color: $text-muted;
        margin: 1 0;
    }

    DataTable {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("o", "show_orphans", "Orphans", show=True),
        Binding("p", "show_projects", "Projects", show=True),
        Binding("d", "confirm_delete", "Delete", show=True),
        Binding("enter", "select_current", "Select", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.discovery = SessionDiscovery()
        self.deleter = SessionDeleter()
        self.projects: list[Project] = []
        self.orphans: list[Session] = []
        self.state = ViewState()
        self._current_sessions: list[Session] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="header-bar"):
            yield Label("[b]CCSM[/b] ", id="app-title")
            yield Label("Projects[p] Orphans[o] Refresh[r]", id="nav-hint")
        with Horizontal(id="main-area"):
            with Vertical(id="left-panel"):
                yield Label("Projects", classes="section-title", id="left-title")
                yield DataTable(id="projects-table")
                yield Static("↑↓ or Click to select project", classes="hint", id="left-hint")
            with Vertical(id="right-panel"):
                yield Label("Sessions", classes="section-title", id="right-title")
                yield DataTable(id="sessions-table")
                yield Static("↑↓ or Click to select session", classes="hint", id="right-hint")
            with Vertical(id="detail-panel"):
                yield Label("Details", classes="section-title")
                yield Static("Select a session", id="detail-text")
                yield Static("", id="action-area")
        yield Footer()

    def on_mount(self) -> None:
        # Set up projects table
        pt = self.query_one("#projects-table", DataTable)
        pt.add_columns("Project", "Sessions")
        pt.cursor_type = "row"
        pt.focus()

        # Set up sessions table
        st = self.query_one("#sessions-table", DataTable)
        st.add_columns("ID", "Status", "Tasks", "Created")
        st.cursor_type = "row"

        self.load_data()

    @on(DataTable.RowSelected, "#projects-table")
    def _on_project_selected(self, event: DataTable.RowSelected) -> None:
        """Handle project selection via mouse click."""
        self.log(f"[DEBUG] _on_project_selected: row={event.cursor_row}")
        self.state = ViewState(
            mode="projects",
            selected_project_index=event.cursor_row,
            selected_session_index=None
        )
        self._update_views()
        self.query_one("#sessions-table", DataTable).focus()

    @on(DataTable.RowHighlighted, "#projects-table")
    def _on_project_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle project highlighting via keyboard."""
        self.log(f"[DEBUG] _on_project_highlighted: row={event.cursor_row}")
        self.state = ViewState(
            mode="projects",
            selected_project_index=event.cursor_row,
            selected_session_index=None
        )
        self._update_views()
        self.query_one("#sessions-table", DataTable).focus()

    @on(DataTable.RowSelected, "#sessions-table")
    def _on_session_selected(self, event: DataTable.RowSelected) -> None:
        """Handle session selection via mouse click."""
        self.log(f"[DEBUG] _on_session_selected: row={event.cursor_row}")
        self.state.selected_session_index = event.cursor_row
        self._update_detail_panel()

    @on(DataTable.RowHighlighted, "#sessions-table")
    def _on_session_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle session highlighting via keyboard."""
        self.log(f"[DEBUG] _on_session_highlighted: row={event.cursor_row}")
        self.state.selected_session_index = event.cursor_row
        self._update_detail_panel()

    def load_data(self) -> None:
        # Invalidate cache first to ensure fresh data after delete operations
        self.discovery.invalidate_cache()

        self.projects = self.discovery.discover_projects()
        self.orphans = self.discovery.get_orphan_sessions()

        # Validate selection based on current mode
        if self.state.mode == "projects":
            if self.projects:
                if self.state.selected_project_index is None:
                    self.state.selected_project_index = 0
                elif self.state.selected_project_index >= len(self.projects):
                    self.state.selected_project_index = len(self.projects) - 1
            else:
                # No projects available - switch to orphans or reset
                self.state.selected_project_index = None
                if self.orphans:
                    self.state.mode = "orphans"

        # Validate orphans mode (previously missing!)
        elif self.state.mode == "orphans":
            if not self.orphans:
                # No orphans - switch back to projects
                self.state.mode = "projects"
                if self.projects:
                    self.state.selected_project_index = 0
                else:
                    self.state.selected_project_index = None

        self.state.selected_session_index = None
        self._update_projects_table()
        self._update_views()

    def _update_projects_table(self) -> None:
        """Update the projects table (call only when data changes)."""
        pt = self.query_one("#projects-table", DataTable)
        pt.clear()

        for i, p in enumerate(self.projects):
            name = p.path
            if name.startswith("/Users/"):
                name = "~" + name[7:]
            if len(name) > 40:
                name = "..." + name[-37:]
            sessions_str = f"{p.session_count}"
            pt.add_row(name, sessions_str, key=str(i))

        # Select the current project in the table
        if self.state.selected_project_index is not None and len(self.projects) > 0:
            try:
                pt.move_cursor(row=self.state.selected_project_index, column=0)
            except Exception:
                pass  # Ignore cursor move errors

    def _update_views(self) -> None:
        # Validate mode matches available data
        if self.state.mode == "projects" and not self.projects:
            # No projects - switch to orphans if available
            if self.orphans:
                self.state.mode = "orphans"
                self.state.selected_project_index = None
            else:
                # Both are empty - reset to projects mode
                self.state.selected_project_index = None
        elif self.state.mode == "orphans" and not self.orphans:
            # No orphans - switch to projects
            self.state.mode = "projects"
            if self.projects:
                self.state.selected_project_index = 0
            else:
                self.state.selected_project_index = None

        # Update sessions table based on current selection
        self._update_sessions_table()

        # Update title to reflect current mode
        if self.orphans:
            self.query_one("#left-title", Label).update(f"Projects ({len(self.projects)}) + Orphans ({len(self.orphans)})")
        else:
            self.query_one("#left-title", Label).update(f"Projects ({len(self.projects)})")

    def _update_sessions_table(self) -> None:
        """Update only the sessions table, keeping projects table stable."""
        st = self.query_one("#sessions-table", DataTable)
        st.clear()

        if self.state.mode == "projects" and self.state.selected_project_index is not None:
            # Validate project index
            if self.state.selected_project_index >= len(self.projects):
                self.state.selected_project_index = None
                self._current_sessions = []
            else:
                self._current_sessions = self.projects[self.state.selected_project_index].sessions
            proj_name = self._shorten_path(self.projects[self.state.selected_project_index].path) if self.state.selected_project_index is not None else "Unknown"
            self.query_one("#right-title", Label).update(f"Sessions in: {proj_name}")
            self.query_one("#right-hint", Static).update(f"[d] Delete selected session")
        elif self.state.mode == "orphans":
            self._current_sessions = self.orphans
            self.query_one("#right-title", Label).update(f"Orphan / Unmapped Sessions ({len(self._current_sessions)})")
            self.query_one("#right-hint", Static).update("[d] Delete selected session")
        else:
            self._current_sessions = []
            self.query_one("#right-title", Label).update("Sessions")
            self.query_one("#right-hint", Static).update("Select a project first")

        for i, s in enumerate(self._current_sessions):
            sid = s.id[:8] + "..."
            status = s.status or "?"
            tasks = str(s.task_count)
            created = s.created_at.strftime("%Y-%m-%d") if s.created_at else "N/A"
            st.add_row(sid, status, tasks, created, key=str(i))

        # Validate selected_session_index against new session count
        if self._current_sessions:
            if self.state.selected_session_index is None:
                self.state.selected_session_index = 0
            elif self.state.selected_session_index >= len(self._current_sessions):
                # Index now out of bounds - reset to last valid or first
                self.state.selected_session_index = len(self._current_sessions) - 1
        else:
            self.state.selected_session_index = None

        # Update detail panel
        self._update_detail_panel()

    def _update_detail_panel(self) -> None:
        detail = self.query_one("#detail-text", Static)
        action = self.query_one("#action-area", Static)

        if self.state.selected_session_index is None:
            detail.update("Select a session to view details\n\nClick a session row to see details\nPress [d] to delete")
            action.update("")
            return

        if self.state.selected_session_index >= len(self._current_sessions):
            detail.update("Select a session to view details")
            action.update("")
            return

        s = self._current_sessions[self.state.selected_session_index]
        info = self.deleter.plan_session_deletion(s.id)

        proj = self._shorten_path(s.project_path) if s.project_path else "(none)"
        created = s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else "N/A"

        text = f"""[b]Session ID[/b]
{s.id}

[b]Project[/b]
{proj}

[b]Status[/b]
{s.status or "unknown"}

[b]Created[/b]
{created}

[b]Counts[/b]
Tasks: {s.task_count}
Todos: {s.todo_count}
Plans: {s.plan_count}

[b]Deletion impact[/b]
Files to delete: {len(info.files_to_delete)}
Files to modify: {len(info.files_to_modify)}"""

        if info.paste_cache_to_delete:
            text += f"\n Paste cache (exclusive): {len(info.paste_cache_to_delete)}"
        if info.paste_cache_shared:
            text += f"\n Paste cache (shared): {len(info.paste_cache_shared)} [will be kept]"

        detail.update(text)
        action.update("[b]Ready to delete[/b]\nPress [d] to confirm")

    def _shorten_path(self, path: str) -> str:
        if path.startswith("/Users/"):
            path = "~" + path[7:]
        if len(path) > 35:
            path = "..." + path[-32:]
        return path

        """Handle selection in a DataTable."""
        self.log(f"[DEBUG] _handle_table_selection: table={table.id}, idx={idx}")
        if idx < 0:
            return

        if table.id == "projects-table":
            self.state = ViewState(
                mode="projects",
                selected_project_index=idx,
                selected_session_index=None
            )
            self.log(f"[DEBUG] Calling _update_views for project {idx}")
            self._update_views()
            self.query_one("#sessions-table", DataTable).focus()

        elif table.id == "sessions-table":
            self.state.selected_session_index = idx
            self._update_detail_panel()

    # Actions
    def action_refresh(self) -> None:
        self.load_data()
        self.notify("Refreshed", severity="information")

    def action_show_projects(self) -> None:
        self.state = ViewState(mode="projects")
        if self.projects:
            self.state.selected_project_index = 0
            self.state.selected_session_index = None
        self._update_views()
        # Focus projects table
        self.query_one("#projects-table", DataTable).focus()

    def action_show_orphans(self) -> None:
        self.state = ViewState(mode="orphans", selected_project_index=None, selected_session_index=None)
        self._update_views()
        # Focus sessions table
        self.query_one("#sessions-table", DataTable).focus()

    def action_select_current(self) -> None:
        """Handle Enter key to select current row."""
        # Get the focused widget
        focused = self.focused
        if focused is None:
            return

        # Check if it's a DataTable
        if isinstance(focused, DataTable):
            # Get current cursor position
            cursor = focused.cursor_row

            if focused.id == "projects-table":
                # Select project
                self.state = ViewState(
                    mode="projects",
                    selected_project_index=cursor,
                    selected_session_index=None
                )
                self._update_views()
                self.query_one("#sessions-table", DataTable).focus()
            elif focused.id == "sessions-table":
                # Select session
                self.state.selected_session_index = cursor
                self._update_detail_panel()

    async def action_confirm_delete(self) -> None:
        if self.state.selected_session_index is None or self.state.selected_session_index >= len(self._current_sessions):
            self.notify("Select a session first", severity="warning")
            return

        s = self._current_sessions[self.state.selected_session_index]

        # In TUI mode, directly delete without confirmation
        # (User has already selected the session, so we assume they intend to delete)
        result = self.deleter.delete_session(s.id, force=True)
        if result.success:
            self.notify(f"Deleted {s.id[:8]}…", severity="success")
            # Clear current session cache to prevent stale data
            self._current_sessions = []
            # Reset selections completely
            self.state.selected_session_index = None
            self.state.selected_project_index = None
            # Deep refresh with cache invalidation
            self.load_data()
        else:
            self.notify(f"Delete failed: {result.errors[0]}", severity="error")


def launch_tui() -> int:
    """Launch the Textual TUI."""
    try:
        app = CCSMApp()
        app.run()
        return 0
    except ImportError as e:
        print("Error: Textual is not installed. Install it with: pip install textual")
        print(f"Details: {e}")
        return 1