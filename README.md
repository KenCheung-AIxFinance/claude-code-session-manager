# Claude Code Session Manager (CCSM)

A CLI and TUI tool for managing Claude Code sessions and projects. List, inspect, and delete sessions with full cleanup of associated data.

## Features

- **List** all projects and their associated sessions
- **Info** - View detailed information about a session before deletion
- **Delete** - Delete specific sessions with proper cleanup
- **Delete Project** - Delete entire projects and all their sessions
- **Cleanup** - Find and remove orphaned sessions
- **Interactive** - Beautiful TUI mode for easy management

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ccsm.git
cd ccsm

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Basic Usage

```bash
# Show help
ccsm --help

# List all projects and sessions
ccsm list

# Show verbose output with details
ccsm list -v

# Output as JSON (for automation)
ccsm list --json
```

![CCSM List Summary](images/cli-list-summary.png)
*Default list view showing projects and orphaned sessions.*

## Commands

### List Projects and Sessions

```bash
# List all projects and orphan sessions
ccsm list

# Filter to a specific project
ccsm list --project "~/Documents/Dev/myproject"

# Show verbose details (task counts, todos, plans)
ccsm list -v

# Machine-readable JSON output
ccsm list --json
```

![CCSM List Verbose](images/cli-list-verbose.png)
*Verbose list view showing detailed task, todo, and plan counts for each session.*

### Session Info

```bash
# Show detailed info about a session
ccsm info <session-id>
```

![CCSM Session Info](images/cli-session-info.png)
*Detailed session information including a preview of files targeted for deletion.*

### Delete a Session

```bash
# Preview what would be deleted (recommended first)
ccsm delete <session-id> --dry-run

# Delete with confirmation prompt
ccsm delete <session-id>

# Delete without confirmation
ccsm delete <session-id> --force
```

![CCSM Delete Dry Run](images/cli-delete-dry-run.png)
*Dry-run mode allows you to safely preview deletion impact before committing.*

### Delete a Project

```bash
# Preview what would be deleted
ccsm delete-project "~/path/to/project" --dry-run

# Delete project (keeps .claude/ directory)
ccsm delete-project "~/path/to/project"

# Delete project AND its .claude/ directory
ccsm delete-project "~/path/to/project" --include-claude-dir
```

### Cleanup Orphaned Sessions

```bash
# List orphaned sessions (sessions without projects)
ccsm cleanup

# Delete all orphaned sessions automatically
ccsm cleanup --auto-remove
```

### Interactive Mode (TUI)

```bash
# Launch interactive TUI
ccsm interactive
# or shorthand
ccsm -i
```

![CCSM TUI Orphans](images/tui-orphan-sessions.png)
*Interactive TUI for browsing and managing sessions with real-time detail preview.*

**TUI Keyboard Shortcuts:**
- `↑↓` - Navigate projects/sessions
- `Enter` - Select
- `D` - Delete selected session
- `P` - Show projects
- `O` - Show orphans
- `R` - Refresh
- `Q` - Quit

## Data Locations

CCSM manages data in the following Claude Code directories:

| Path | Description |
|------|-------------|
| `~/.claude/tasks/{session_id}/` | Task files |
| `~/.claude/todos/` | Todo files (matched by session ID) |
| `~/.claude/plans/*.md` | Saved Markdown plans (global, not auto-deleted) |
| `~/.claude/sessions/*.json` | Session marker files |
| `~/.claude/session-env/{session_id}/` | Environment variables |
| `~/.claude/teams/{session_id}/` | Team data directories |
| `~/.claude/file-history/{session_id}/` | File edit history |
| `~/.claude/debug/{session_id}.txt` | Debug logs |
| `~/.claude/telemetry/` | Telemetry events |
| `~/.claude/paste-cache/` | Paste content cache (reference-counted) |
| `~/.claude/history.jsonl` | Conversation history (rewritten on session delete) |

## Important Notes

- Always use `--dry-run` first to preview what will be deleted
- `paste-cache` files are shared across sessions with reference counting
- Global plans (`~/.claude/plans/*.md`) are never automatically deleted
- The safest way to clean orphans is `ccsm delete <orphan-id> --force` one at a time
- `history.jsonl` is rewritten using streaming (preserves invalid JSON lines)

---

## For Developers

### Project Structure

```
ccsm/
├── ccsm/
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── cli/
│   │   ├── commands.py      # CLI command handlers
│   │   ├── formatters.py    # Output formatting
│   │   └── tui.py           # Textual TUI
│   ├── core/
│   │   ├── discovery.py     # Session/project discovery
│   │   ├── deleter.py       # Deletion logic
│   │   └── models.py        # Data models
│   └── utils/
├── SPEC.md                  # Design specification
├── pyproject.toml           # Package configuration
└── README.md                # This file
```

### Adding New Commands

1. Add argument parser in `ccsm/cli/commands.py` → `create_parser()`
2. Add handler function (e.g., `cmd_xxx`)
3. Register handler in `main()` → `command_handlers` dict

### Key Classes

- `SessionDiscovery` - Discovers sessions and projects from `~/.claude/`
- `SessionDeleter` - Handles deletion of sessions and projects
- `Session` / `Project` - Data models
- `SessionInfo` - Deletion planning (files to delete)
- `DeleteResult` - Result of deletion operation

### Running Tests

```bash
# Activate venv
source venv/bin/activate

# Run tests
pytest

# With coverage
pytest --cov=ccsm
```

### Dependencies

- Python 3.10+
- `rich>=13.0.0` - Rich CLI output
- `questionary>=1.10.0` - Interactive prompts
- `textual>=0.90.0` - TUI framework

## License

MIT