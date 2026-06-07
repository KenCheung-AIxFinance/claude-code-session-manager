# Release v1.0.0 - Initial Public Release 🚀

We are excited to announce the first official release of **Claude Code Session Manager (CCSM)**! This tool is designed to help users of Anthropic's Claude Code CLI manage their local session data, projects, and orphaned resources with ease.

## ✨ Core Features

*   **Session Discovery**: Automatically maps Claude Code sessions to their respective local project directories.
*   **Interactive TUI**: A beautiful terminal interface built with `textual` for browsing, inspecting, and deleting sessions in real-time.
*   **Intelligent Session Naming**: Automatically extracts session titles from conversation history, prioritizing custom titles or the first meaningful user prompt.
*   **Comprehensive Cleanup**: Deep deletion of session-related data including:
    *   Tasks and Todos
    *   Environment variables and Debug logs
    *   File history snapshots and Telemetry
    *   Reference-counted Paste-cache
    *   Streaming rewrite of `history.jsonl`
*   **Orphan Management**: Identify and clean up "orphan" sessions that no longer have a valid transcript or project link.
*   **JSON Support**: Full machine-readable output for `list` commands, perfect for automation and scripting.

## 🚀 Getting Started

### Installation

```bash
git clone https://github.com/KenCheung-AIxFinance/claude-code-session-manager.git
cd ccsm
pip install -e .
```

### Basic Commands

```bash
ccsm list           # List all projects and sessions
ccsm info <id>      # Inspect a specific session
ccsm delete <id>    # Delete a session with confirmation
ccsm -i             # Launch the interactive TUI
```

## 🛠 Project Status

This is the initial stable release. CCSM is designed to be a safe and efficient companion for heavy Claude Code users.

---
*Thank you for using CCSM! If you encounter any issues or have feature requests, please open an issue on our GitHub repository.*
