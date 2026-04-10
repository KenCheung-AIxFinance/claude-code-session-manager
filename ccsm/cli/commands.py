"""CLI commands for CCSM."""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from ccsm.core import SessionDiscovery, SessionDeleter
from ccsm.cli.formatters import (
    format_list_output,
    format_info_output,
    format_delete_result,
    format_cleanup_result,
)


console = Console()


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="ccsm",
        description="Claude Code Session Manager - Manage and delete Claude Code sessions and projects.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="ccsm 1.0.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List all projects and sessions")
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    list_parser.add_argument(
        "--project",
        type=str,
        help="Only list sessions for a specific project",
    )
    list_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show more details (task counts, etc.)",
    )

    # Info command
    info_parser = subparsers.add_parser("info", help="Show detailed info about a session")
    info_parser.add_argument(
        "session_id",
        type=str,
        help="Session ID to show info for",
    )

    # Delete session command
    delete_session_parser = subparsers.add_parser("delete", help="Delete a session")
    delete_session_parser.add_argument(
        "session_id",
        type=str,
        help="Session ID to delete",
    )
    delete_session_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without actually deleting",
    )
    delete_session_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Skip confirmation for active sessions",
    )
    delete_session_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed deletion progress",
    )

    # Delete project command
    delete_project_parser = subparsers.add_parser("delete-project", help="Delete a project and all its sessions")
    delete_project_parser.add_argument(
        "project_path",
        type=str,
        help="Project path to delete",
    )
    delete_project_parser.add_argument(
        "--include-claude-dir",
        action="store_true",
        help="Also delete the project's .claude/ directory",
    )
    delete_project_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without actually deleting",
    )
    delete_project_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Skip confirmation prompts",
    )
    delete_project_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed deletion progress",
    )

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up orphaned sessions (without projects)")
    cleanup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be cleaned up without actually cleaning",
    )
    cleanup_parser.add_argument(
        "--auto-remove",
        action="store_true",
        help="Automatically remove orphaned data without prompting",
    )

    # Interactive command
    subparsers.add_parser("interactive", aliases=["i"], help="Launch interactive TUI mode")

    return parser


def cmd_list(args: argparse.Namespace) -> int:
    """Handle the 'list' command."""
    discovery = SessionDiscovery()

    if args.project:
        # Normalize the path: expand ~ and remove trailing slashes
        normalized_project = os.path.normpath(os.path.expanduser(args.project))
        project = discovery.get_project_by_path(normalized_project)
        if not project:
            console.print(f"[red]Project not found: {args.project}[/red]")
            return 1

        sessions = project.sessions
        if args.json:
            import json
            output = {
                "project": args.project,
                "sessions": [
                    {
                        "id": s.id,
                        "status": s.status,
                        "createdAt": s.created_at.isoformat() if s.created_at else None,
                        "taskCount": s.task_count,
                        "todoCount": s.todo_count,
                        "planCount": s.plan_count,
                    }
                    for s in sessions
                ],
            }
            print(json.dumps(output, indent=2))
        else:
            format_list_output(projects=[project], verbose=args.verbose)
    else:
        projects = discovery.discover_projects()
        orphans = discovery.get_orphan_sessions()

        if args.json:
            import json
            output = {
                "projects": [
                    {
                        "path": p.path,
                        "sessionCount": p.session_count,
                        "sessions": [
                            {
                                "id": s.id,
                                "status": s.status,
                                "createdAt": s.created_at.isoformat() if s.created_at else None,
                                "taskCount": s.task_count,
                                "todoCount": s.todo_count,
                                "planCount": s.plan_count,
                            }
                            for s in p.sessions
                        ],
                    }
                    for p in projects
                ],
                "orphanSessions": [
                    {
                        "id": s.id,
                        "status": s.status,
                        "createdAt": s.created_at.isoformat() if s.created_at else None,
                    }
                    for s in orphans
                ],
            }
            print(json.dumps(output, indent=2))
        else:
            format_list_output(projects=projects, orphan_sessions=orphans, verbose=args.verbose)

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Handle the 'info' command."""
    discovery = SessionDiscovery()
    deleter = SessionDeleter()

    session = discovery.get_session_by_id(args.session_id)
    if not session:
        console.print(f"[red]Session not found: {args.session_id}[/red]")
        return 1

    info = deleter.plan_session_deletion(args.session_id)
    format_info_output(session, info)
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    """Handle the 'delete' command."""
    deleter = SessionDeleter(dry_run=args.dry_run)

    # First show what will be deleted
    info = deleter.plan_session_deletion(args.session_id)

    if args.dry_run:
        console.print("[yellow]DRY RUN - No files will be actually deleted[/yellow]\n")

    format_info_output(info.session, info)

    if not args.dry_run and not args.force:
        console.print("\n[yellow]This will delete the session and its associated data.[/yellow]")
        response = input("Continue? [y/N] ")
        if response.lower() != "y":
            console.print("[yellow]Cancelled.[/yellow]")
            return 1

    result = deleter.delete_session(args.session_id, force=args.force)
    format_delete_result(result, verbose=args.verbose, dry_run=args.dry_run)

    return 0 if result.success else 1


def cmd_delete_project(args: argparse.Namespace) -> int:
    """Handle the 'delete-project' command."""
    deleter = SessionDeleter(dry_run=args.dry_run)

    # Normalize the path: expand ~ and remove trailing slashes
    normalized_path = os.path.normpath(os.path.expanduser(args.project_path))
    project = SessionDiscovery().get_project_by_path(normalized_path)
    if not project:
        console.print(f"[red]Project not found: {args.project_path}[/red]")
        return 1

    if args.dry_run:
        console.print("[yellow]DRY RUN - No files will be actually deleted[/yellow]\n")

    console.print(f"[bold]Project:[/bold] {project.path}")
    console.print(f"[bold]Sessions to delete:[/bold] {project.session_count}")

    for session in project.sessions:
        info = deleter.plan_session_deletion(session.id)
        console.print(f"  - {session.id} ({info.total_files} files)")

    if args.include_claude_dir:
        console.print(f"  - {normalized_path}/.claude/ (project config)")

    if not args.dry_run and not args.force:
        console.print("\n[yellow]This will delete all sessions and optionally the project config.[/yellow]")
        response = input("Continue? [y/N] ")
        if response.lower() != "y":
            console.print("[yellow]Cancelled.[/yellow]")
            return 1

    result = deleter.delete_project(
        normalized_path,
        include_claude_dir=args.include_claude_dir,
        force=args.force,
    )
    format_delete_result(result, verbose=args.verbose, dry_run=args.dry_run)

    return 0 if result.success else 1


def cmd_cleanup(args: argparse.Namespace) -> int:
    """Handle the 'cleanup' command."""
    deleter = SessionDeleter(dry_run=args.dry_run)

    if args.dry_run:
        console.print("[yellow]DRY RUN - No files will be actually cleaned[/yellow]\n")

    result = deleter.cleanup(auto_remove=args.auto_remove)
    format_cleanup_result(result)

    return 0


def cmd_interactive(args: argparse.Namespace) -> int:
    """Handle the 'interactive' command - launch TUI."""
    try:
        from ccsm.cli.tui import launch_tui
        return launch_tui()
    except ImportError:
        console.print("[red]TUI not yet implemented. Use CLI commands instead.[/red]")
        return 1


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Dispatch to command handlers
    command_handlers = {
        "list": cmd_list,
        "info": cmd_info,
        "delete": cmd_delete,
        "delete-project": cmd_delete_project,
        "cleanup": cmd_cleanup,
        "interactive": cmd_interactive,
    }

    handler = command_handlers.get(args.command)
    if handler:
        try:
            return handler(args)
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted.[/yellow]")
            return 130
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if "--verbose" in sys.argv or "-v" in sys.argv:
                import traceback
                traceback.print_exc()
            return 1
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())