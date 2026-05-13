"""Output formatters for CCSM CLI."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from ccsm.core.models import DeleteResult, Session, SessionInfo

console = Console()


def format_list_output(
    projects: list,
    orphan_sessions: list[Session] = None,
    verbose: bool = False,
) -> None:
    """Format and print the list output.

    Args:
        projects: List of Project objects.
        orphan_sessions: List of orphan Session objects.
        verbose: Show additional details.
    """
    if not projects and not orphan_sessions:
        console.print("[yellow]No projects or sessions found.[/yellow]")
        return

    # Calculate totals
    total_sessions = sum(p.session_count for p in projects)
    if orphan_sessions:
        total_sessions += len(orphan_sessions)

    # Print header
    console.print(f"\n[bold cyan]Claude Code Session Manager[/bold cyan]")
    console.print(f"Projects: {len(projects)} | Sessions: {total_sessions}")
    console.print()

    # Print projects
    for project in projects:
        path_short = project.path
        if path_short.startswith("/Users/"):
            path_short = "~" + path_short[7:]

        status_icon = "[green]✓[/green]" if project.session_count > 0 else "[dim]○[/dim]"

        if verbose:
            console.print(f"{status_icon} {path_short} [dim]({project.session_count} sessions)[/dim]")
            for session in project.sessions:
                status_marker = "●active" if session.status == "in_progress" else ""
                updated = (session.updated_at or session.created_at)
                updated_str = updated.strftime("%Y-%m-%d") if updated else "unknown"
                title = f" [cyan]{session.name}[/cyan]" if session.name else ""
                console.print(f" ├── {session.id} [{updated_str}] {status_marker}{title}")
                if verbose:
                    console.print(f" │ tasks:{session.task_count} todos:{session.todo_count} plans:{session.plan_count}")
        else:
            console.print(f"{status_icon} {path_short} [dim]({project.session_count} sessions)[/dim]")

    # Print orphans
    if orphan_sessions:
        console.print()
        console.print("[bold]Orphan or unmapped sessions:[/bold]")
        for session in orphan_sessions:
            created = session.created_at.strftime("%Y-%m-%d") if session.created_at else "unknown"
            console.print(f" • {session.id} [{created}]")


def format_info_output(session: Session, info: SessionInfo) -> None:
    """Format and print session info.

    Args:
        session: The Session object.
        info: The SessionInfo with deletion plan.
    """
    if not session:
        console.print("[red]Session not found[/red]")
        return

    # Session details panel
    details = []
    if session.name:
        details.append(f"[bold]Title:[/bold] {session.name}")
    details.append(f"[bold]Session ID:[/bold] {session.id}")
    details.append(f"[bold]Project:[/bold] {session.project_path or 'None'}")
    details.append(f"[bold]Status:[/bold] {session.status}")
    if session.updated_at:
        details.append(f"[bold]Updated:[/bold] {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if session.created_at:
        details.append(f"[bold]Created:[/bold] {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    details.append(f"[bold]Tasks:[/bold] {session.task_count}")
    details.append(f"[bold]Todos:[/bold] {session.todo_count}")
    details.append(f"[bold]Plans:[/bold] {session.plan_count}")

    panel = Panel(
        "\n".join(details),
        title="Session Info",
        border_style="cyan",
    )
    console.print(panel)

    # Files to delete
    console.print(f"\n[bold]Files to delete:[/bold] {len(info.files_to_delete)}")

    if info.files_to_delete:
        for f in info.files_to_delete[:10]:
            console.print(f" • {f}")
        if len(info.files_to_delete) > 10:
            console.print(f" ... and {len(info.files_to_delete) - 10} more")

    # Paste-cache handling
    if info.paste_cache_to_delete:
        console.print(f"\n[yellow]Paste cache (exclusive, will delete):[/yellow]")
        for f in info.paste_cache_to_delete:
            console.print(f" • {f}")

    if info.paste_cache_shared:
        console.print(f"\n[dim]Paste cache (shared, will keep):[/dim]")
        for f in info.paste_cache_shared:
            console.print(f" • {f}")

    # Files to modify
    if info.files_to_modify:
        console.print(f"\n[bold]Files to modify:[/bold]")
        for f in info.files_to_modify:
            console.print(f" • {f}")


def format_delete_result(
    result: DeleteResult, verbose: bool = False, dry_run: bool = False
) -> None:
    """Format and print delete result.

    Args:
        result: The DeleteResult object.
        verbose: Show detailed progress.
        dry_run: If True, format output for dry-run mode.
    """
    if result.success:
        if dry_run:
            console.print(
                f"[yellow]DRY RUN: would delete {result.total_deleted} items[/yellow]"
            )
        else:
            console.print(
                f"[green]✓ Successfully deleted {result.total_deleted} items[/green]"
            )
    else:
        console.print(f"[red]✗ Deletion completed with errors[/red]")

    if result.deleted_files and verbose:
        console.print("\n[bold]Deleted files:[/bold]")
        for f in result.deleted_files[:20]:
            console.print(f" • {f}")
        if len(result.deleted_files) > 20:
            console.print(f" ... and {len(result.deleted_files) - 20} more")

    if result.modified_files:
        console.print("\n[bold]Modified files:[/bold]")
        for f in result.modified_files:
            console.print(f" • {f}")

    if result.skipped_files:
        console.print("\n[yellow]Skipped files:[/yellow]")
        for f in result.skipped_files:
            console.print(f" • {f}")

    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for e in result.errors:
            console.print(f" • {e}")


def format_cleanup_result(result: DeleteResult) -> None:
    """Format and print cleanup result.

    Args:
        result: The DeleteResult object.
    """
    if result.skipped_files and not result.deleted_files:
        console.print("\n[bold]Orphaned sessions found:[/bold]")
        for f in result.skipped_files:
            console.print(f" • {f}")
        console.print("\n[yellow]Run with --auto-remove to clean these up.[/yellow]")
    elif result.deleted_files:
        console.print(f"[green]✓ Cleaned up {len(result.deleted_files)} orphaned items[/green]")
    else:
        console.print("[green]No orphaned sessions to clean up.[/green]")