# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Code Session Manager (CCSM) — a CLI + TUI tool for managing Claude Code sessions and projects. Allows listing, inspecting, and deleting sessions and associated data. Not related to OMC (oh-my-claudecode).

## Architecture

The tool manages data in `~/.claude/` with these key relationships:

- **Session → Project**: mapped via `workingDirectory` in `history.jsonl` and/or transcripts directory structure
- **Session ID format**: UUID (e.g., `012e2e2d-fde5-4146-bc11-15a436a8d46b`)
- **Todo file format**: `{session_id}-agent-{session_id}.json`

### Claude Code data locations (current)

**Global** (under `~/.claude/`):
- `tasks/{session_id}/` - task files (1.json, 2.json...)
- `todos/` - todo JSON files matching session ID
- `plans/*.md`, `plans/*.json` - global plan files in `~/.claude/plans/`
- `sessions/*.json` - session metadata and PID-based marker files
- `session-env/{session_id}/` - environment variables for session
- `teams/{session_id}/` - team data directory
- `file-history/{session_id}/` - file edit history snapshots
- `debug/{session_id}.txt` - debug logs
- `telemetry/1p_failed_events.{session_id}.*.json` - telemetry data
- `projects/{path_hash}/{session_id}.jsonl` - per-session transcript files grouped by project hash
- `history.jsonl` - conversation history (sessionId per line)
- `paste-cache/{hash}.txt` - pasted content cache (shared across sessions, reference-counted)

**Per-project** (in the project's `.claude/`):
- `commands/` - custom slash commands
- `settings.json` - project settings
- `memory.json` - project memory
- `plans/` - project-specific plans (currently not used)

### Key deletion behaviors (current)

- **Session deletion** removes:
  - `tasks/{session_id}/`
  - `todos/*{session_id}*`
  - `session-env/{session_id}/`
  - `file-history/{session_id}/`
  - `debug/{session_id}.txt`
  - `telemetry/1p_failed_events.{session_id}.*.json`
  - `teams/{session_id}/`
  - `projects/{path_hash}/{session_id}.jsonl`
  - `sessions/*.json` (PID marker matching this sessionId)
  - `plans/*.md`, `plans/*.json` (only when uniquely referenced by this session; shared global plans are kept)
  - `paste-cache/{hash}.txt` (only if no other sessions reference it - reference counted)
  - Entries in `history.jsonl` (streaming rewrite, preserves invalid lines)

- **Discovery visibility**:
  - Sessions with a transcript but missing `history.jsonl` project mapping are surfaced as orphan/unmapped sessions instead of becoming invisible.

- **Project deletion** removes all sessions in the project, plus optionally the project's `.claude/` directory (`--include-claude-dir`).

- **Plans**: Global `~/.claude/plans/` files are deleted only when uniquely referenced by the session being removed; shared global plans are kept. Project-level plans are deleted only when using `--include-claude-dir`.

- **Orphan sessions**: Sessions that have data in data directories (tasks/, todos/, etc.) but no corresponding .jsonl transcript file in projects/, plus transcript-bearing sessions that lost their project mapping. These can be cleaned with `ccsm cleanup`.

## Commands (actual CLI)

```bash
# List all projects and sessions
ccsm list                              # Show all projects + orphans
ccsm list -v                           # Verbose: show per-session details
ccsm list --json                       # JSON output (machine-readable)
ccsm list --project "~/path/to/project"  # Filter to specific project

# Query session details
ccsm info <session_id>                 # Show session info + deletion plan

# Delete a session
ccsm delete <session_id> -n            # Preview what would be deleted
ccsm delete <session_id> -y            # Actually delete (no confirmation)

# Delete a project (all its sessions)
ccsm delete-project "~/path/to/project" -n
ccsm delete-project "~/path/to/project" --include-claude-dir -y

# Clean up orphaned sessions
ccsm cleanup                           # List orphans (dry-run by default)
ccsm cleanup -y                        # Delete all orphans (CAUTION: large blast radius)
# Safer alternative: delete specific orphan
ccsm delete <orphan_session_id> -y
```

## Usage Scenarios for Agents

### Scenario 1: Find and delete a specific session by ID

```bash
# 1. List all sessions (get IDs)
ccsm list --json | jq '.projects[].sessions[] | .id'

# 2. Check what would be deleted
ccsm delete <session_id> -n

# 3. Actually delete
ccsm delete <session_id> -y
```

### Scenario 2: Delete all sessions in a project

```bash
# 1. Preview what will be deleted
ccsm delete-project "~/Documents/Dev/myproject" -n

# 2. Delete project + its .claude/ directory
ccsm delete-project "~/Documents/Dev/myproject" --include-claude-dir -y
```

### Scenario 3: Clean up orphaned sessions safely

```bash
# 1. See orphan list
ccsm cleanup

# 2. Delete ONE specific orphan (recommended for safety)
ccsm delete <orphan_session_id> -y

# 3. Repeat for each orphan you want to remove
```

### Scenario 4: Get machine-readable session list for automation

```bash
# Get all session IDs
ccsm list --json | jq -r '.projects[].sessions[].id'

# Get sessions for a specific project
ccsm list --project "~/Documents/Dev/myproject" --json | jq '.sessions[].id'

# Get sessions with their metadata
ccsm list --json | jq '.projects[] | {project: .path, sessions: [.sessions[] | {id: .id, status: .status, taskCount: .taskCount}]}'
```

### Scenario 5: Use with external tools

```bash
# Export session list to file
ccsm list --json > sessions.json

# Check if a specific session exists
ccsm info <session_id> && echo "Session exists" || echo "Session not found"
```

## Important Notes for Agents

1. **Always preview first**: Use `-n` or `--dry-run` with `delete` and `delete-project` to preview what will be deleted. Note that `cleanup` is a dry-run by default unless you provide `-y`.

2. **Path normalization**: Both `~/path` and `/full/path/` work with `--project` and `delete-project`.

3. **Reference counting**: `paste-cache` files are shared across sessions. Deleting one session will only remove a cache file if no other sessions reference it.

4. **history.jsonl safety**: When deleting sessions, history.jsonl is rewritten using streaming (not line-by-line deletion), and invalid JSON lines are preserved.

5. **Plan deletion is reference-aware**: Global plans in `~/.claude/plans/` are deleted only when uniquely referenced by the session being removed; shared plans are kept.

6. **Orphan cleanup**: The safest way is `ccsm delete <orphan_id> -y` one at a time. Avoid `ccsm cleanup -y` (or `-a`, `--auto-remove`) unless you're certain (it deletes ALL orphan/unmapped sessions).

## Design Spec

`SPEC.md` describes the intended behavior; if there is any mismatch, the implementation and the CLI output are authoritative.