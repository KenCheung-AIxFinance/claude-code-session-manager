# Claude Code Session Manager (CCSM)

A CLI tool for managing and deleting Claude Code sessions and projects.

## Features

- **List** all projects and their associated sessions
- **Info** - View detailed information about a session before deletion
- **Delete** - Delete specific sessions with proper cleanup
- **Delete Project** - Delete entire projects and all their sessions
- **Cleanup** - Find and remove orphaned sessions
- **Interactive** - TUI mode (coming soon)

## Quick Start

```bash
# Activate virtual environment (required)
source venv/bin/activate

# Show help
ccsm --help
```

## Usage

### List all projects and sessions

```bash
ccsm list                              # Show all projects + orphans
ccsm list --json                       # Machine-readable JSON output
ccsm list --project "~/path/to/project"  # Filter to specific project
ccsm list -v                           # Verbose: show per-session details
```

### Show session info

```bash
ccsm info <session-id>                 # Show session details + what would be deleted
```

### Delete a session

```bash
ccsm delete <session-id> --dry-run     # Preview what would be deleted
ccsm delete <session-id> --force       # Actually delete (skips confirmation)
```

### Delete a project

```bash
ccsm delete-project "~/path/to/project" --dry-run
ccsm delete-project "~/path/to/project" --include-claude-dir  # Also delete .claude/ dir
```

### Cleanup orphaned sessions

```bash
ccsm cleanup --dry-run                 # List orphans (sessions without projects)

# Safe cleanup (recommended - delete one at a time):
ccsm delete <orphan-session-id> --force

# Bulk cleanup (CAUTION - deletes ALL orphans):
ccsm cleanup --auto-remove
```

## Data Locations

CCSM manages data in the following Claude Code directories:

| Path | Description |
|------|-------------|
| `~/.claude/tasks/{session_id}/` | Task directories |
| `~/.claude/todos/` | Todo files (matched by session ID) |
| `~/.claude/plans/*.md` | Saved Markdown plans (global, not auto-deleted) |
| `~/.claude/session-env/{session_id}/` | Environment variables |
| `~/.claude/teams/{session_id}/` | Team data directories |
| `~/.claude/sessions/*.json` | Session marker files (by PID) |
| `~/.claude/file-history/{session_id}/` | File edit history |
| `~/.claude/debug/{session_id}.txt` | Debug logs |
| `~/.claude/telemetry/` | Telemetry events |
| `~/.claude/paste-cache/` | Paste content cache (reference counted - only deleted if no other sessions use it) |
| `~/.claude/history.jsonl` | Conversation history (rewritten on session delete) |

## Path Normalization

Both `~` expansion and trailing slashes are handled:

```bash
ccsm list --project "~/Documents/Dev/my-project"
ccsm list --project "/Users/you/Documents/Dev/my-project/"
```

## Important Notes

- Always use `--dry-run` first to preview what will be deleted
- `paste-cache` files are shared across sessions and reference-counted (safe deletion)
- Global plans (`~/.claude/plans/*.md`) are never automatically deleted (may be user-created)
- The safest way to clean orphans is `ccsm delete <orphan-id> --force` one at a time
- `history.jsonl` is rewritten using streaming (preserves invalid JSON lines)

## License

MIT