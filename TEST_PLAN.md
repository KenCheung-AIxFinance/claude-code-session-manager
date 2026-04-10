# CCSM Test Plan (command-level)

This file is the authoritative, human+agent-readable test plan for CCSM.

> Note: The built-in Task tool list is not reliable in this environment, so this file is the source of truth.

## Status Summary (as of 2026-04-10)

### ✅ Core Features - Working
- `ccsm list` / `--json` / `--project` / `-v`
- Path normalization (`~/path`, trailing `/`)
- `ccsm info <session_id>` with full deletion plan
- `ccsm delete <session_id>` (dry-run + actual)
- `ccsm delete-project` (dry-run + actual + `--include-claude-dir`)
- `ccsm cleanup --dry-run`
- Safe orphan cleanup: `ccsm delete <orphan_id> --force` (one at a time)
- history.jsonl rewrite preserves bad lines
- Teams and sessions marker files included in deletion scope

### ❌ Not Implemented / Deferred
- Plan (.md) reference detection and deletion
- `ccsm cleanup --auto-remove` safety params (`--limit`, `--session-id`)

---

## Legend
- [ ] Not started
- [~] In progress
- [x] Done

---

# CCSM Test Plan (command-level)

This file is the authoritative, human+agent-readable test plan for CCSM.

> Note: The built-in Task tool list is currently not reliable in this environment (status updates fail schema validation),
> so this file is the source of truth.

## Legend
- [ ] Not started
- [~] In progress
- [x] Done

---

## 0. Setup / sanity
- [x] Activate venv: `source venv/bin/activate`
- [x] CLI help works: `ccsm --help`
- [x] Version prints: `ccsm --version`

## 1. list
### 1.1 Basic output
- [x] `ccsm list` prints header + projects + orphans
- [x] `ccsm list -v` prints per-session rows with counts

### 1.2 JSON output
- [x] `ccsm list --json` prints valid JSON
- [x] JSON contains: projects[].path, sessionCount, sessions[].id/status/createdAt/taskCount/todoCount/planCount

### 1.3 Project filter & path normalization
- [x] `ccsm list --project "/Users/..."` works
- [x] `ccsm list --project "~/..."` works (tilde expansion)
- [x] `ccsm list --project "/Users/.../"` works (trailing slash)
- [x] `ccsm list --project nonexistent` exits non-zero with "Project not found"

## 2. info
- [x] `ccsm info <valid_session_id>` prints session panel + deletion plan
- [x] `ccsm info <nonexistent>` exits non-zero with "Session not found"
- [x] `ccsm info` (missing arg) exits with argparse error

### 2.1 Deletion plan coverage (what shows up in “Files to delete”)
- [x] tasks/{session_id}/ detected
- [x] todos/*{session_id}* detected when present
- [x] session-env/{session_id}/ detected when present
- [x] file-history/{session_id}/ detected when present
- [x] debug/{session_id}.txt detected when present
- [x] telemetry/1p_failed_events.{session_id}.*.json detected when present
- [x] teams/{session_id}/ detected when present
- [x] sessions/*.json PID-marker detected when present
- [x] paste-cache exclusive/shared classification works when cache file exists

## 3. delete (session)
### 3.1 Dry-run
- [x] `ccsm delete <session_id> --dry-run` prints DRY RUN header
- [x] Dry-run summary says `DRY RUN: would delete ...` (not “Successfully deleted”)

### 3.2 Safety / errors
- [x] `ccsm delete <nonexistent> --dry-run` prints plan (0 files) + error result
- [ ] Active session deletion requires --force (needs a reproducible active session to test)

### 3.3 End-to-end delete verification (uses test session)
- [x] Use session: `ccsm-test-and-fix`
  - [x] `ccsm delete ccsm-test-and-fix --dry-run` shows tasks + teams
  - [x] Run: `ccsm delete ccsm-test-and-fix --force`
  - [x] Verify removed: `~/.claude/tasks/ccsm-test-and-fix/`
  - [x] Verify removed: `~/.claude/teams/ccsm-test-and-fix/`
  - [x] Verify history.jsonl rewritten and still parseable (invalid lines preserved)

## 4. delete-project
### 4.1 Dry-run
- [x] `ccsm delete-project <valid_path> --dry-run` lists sessions to delete
- [x] `ccsm delete-project <nonexistent> --dry-run` exits non-zero with "Project not found"

### 4.2 Path normalization
- [x] `ccsm delete-project "~/..." --dry-run` works
- [x] `ccsm delete-project "/Users/.../" --dry-run` works

### 4.3 include-claude-dir behavior
- [x] `ccsm delete-project <path> --include-claude-dir --dry-run` lists `.claude/` deletion
- [ ] Non-dry-run: verify project `.claude/` directory removed (run only on a safe test project)

## 5. cleanup
### 5.1 Dry-run
- [x] `ccsm cleanup --dry-run` prints orphan sessions list

### 5.2 auto-remove (safer alternative: use `ccsm delete <orphan_id> --force`)
- [x] `ccsm delete <orphan_id> --force` successfully removes orphan session (tested with 1dc6d248...)
- [x] Orphan session count decreases after delete

## 6. history.jsonl rewrite robustness
- [x] Code updated to preserve invalid JSON lines on rewrite
- [x] Regression test: after deleting sessions, history.jsonl still parseable with 0 bad lines

## 7. Plan (.md) deletion
- [ ] Deferred: plan reference detection in history.jsonl not yet specified; do not delete global plans by default
