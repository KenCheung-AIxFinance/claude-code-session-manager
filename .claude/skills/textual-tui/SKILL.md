---
name: textual-tui
description: |
  Guide for building terminal user interface (TUI) applications with the Textual Python library.
  Use this skill whenever the user asks to build a TUI, terminal app, CLI interface, or dashboard
  using Python — especially when they mention Textual, Rich, or want an interactive terminal UI.
  Also trigger when user wants to: add widgets to a terminal app, handle keyboard input in TUI,
  create multi-pane layouts, build reactive data displays, or make any Python program interactive
  in a terminal. Always use this skill before writing any Textual code to avoid version mistakes.
---

# Textual TUI Skill

## ⚠️ Version Check — Do This First

Before writing any code, verify the installed version:
```bash
pip show textual
```

**Current stable release: `8.2.3` (April 2026)**  
**Required Python: ≥ 3.9**

If not installed:
```bash
pip install textual           # core library
pip install textual-dev       # devtools (textual CLI, live preview)
```

For TextArea syntax highlighting:
```bash
pip install "textual[syntax]"
```

---

## Architecture Overview

A Textual app has three layers:

```
App (textual.app.App)
 └─ Screen (textual.screen.Screen)   ← one Screen active at a time
     └─ Widgets                       ← composable UI elements
         ├─ Built-in widgets          ← Button, Input, DataTable, etc.
         └─ Custom Widget subclasses
```

Every widget sits in a **DOM tree**. Layout, styling, and events all flow through this tree.

---

## Minimal Boilerplate

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static

class MyApp(App):
    CSS = """
    Static {
        padding: 1;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Hello, World!")
        yield Footer()

if __name__ == "__main__":
    MyApp().run()
```

**Critical rules:**
- `compose()` → uses `yield`, returns `ComposeResult`
- `CSS` class variable → inline Textual CSS (TCSS)
- `BINDINGS` → list of `(key, action, description)` tuples
- `self.app.exit()` or `self.exit()` → quit the app

---

## Key Concepts Quick Reference

| Concept | What it does | Where to read |
|---|---|---|
| `compose()` | Declare widget tree | [api-patterns.md](references/api-patterns.md) |
| `on_mount()` | Run code after widgets attach | [api-patterns.md](references/api-patterns.md) |
| `reactive` | Auto-updating state variables | [api-patterns.md](references/api-patterns.md) |
| `@on(Event)` decorator | Handle widget events | [events-messages.md](references/events-messages.md) |
| BINDINGS | Keyboard shortcuts | [api-patterns.md](references/api-patterns.md) |
| TCSS layout | Flexbox-like CSS for terminal | [layout-css.md](references/layout-css.md) |
| `query_one()` / `query()` | DOM selection | [api-patterns.md](references/api-patterns.md) |
| Workers | Background async tasks | [api-patterns.md](references/api-patterns.md) |
| Screens | Multi-page navigation | [api-patterns.md](references/api-patterns.md) |

---

## Built-in Widgets Catalogue

**Display:**  
`Static`, `Label`, `Digits`, `ProgressBar`, `Sparkline`, `RichLog`, `Log`, `Markdown`, `MarkdownViewer`, `Pretty`, `Rule`, `Placeholder`

**Input:**  
`Button`, `Input`, `TextArea`, `MaskedInput`, `Checkbox`, `RadioButton`, `RadioSet`, `Switch`, `Select`, `SelectionList`

**Layout/Navigation:**  
`Header`, `Footer`, `TabbedContent`, `Tabs`, `ContentSwitcher`, `Collapsible`, `ListView`, `ListItem`, `OptionList`

**Data:**  
`DataTable`, `Tree`, `DirectoryTree`

**Containers (from `textual.containers`):**  
`Horizontal`, `Vertical`, `ScrollableContainer`, `Center`, `Middle`, `Grid`

**Feedback:**  
`Toast`, `LoadingIndicator`, `Link`

---

## Common Patterns Cheat Sheet

### Event handling
```python
from textual import on
from textual.widgets import Button

# Option 1: @on decorator (preferred)
@on(Button.Pressed, "#my-button")
def handle_button(self, event: Button.Pressed) -> None:
    self.notify("Clicked!")

# Option 2: on_<EventName> method
def on_button_pressed(self, event: Button.Pressed) -> None:
    self.notify("Clicked!")
```

### Reactive state
```python
from textual.reactive import reactive

class MyWidget(Widget):
    count: reactive[int] = reactive(0)

    def watch_count(self, value: int) -> None:
        self.query_one("#counter", Label).update(f"Count: {value}")
```

### DOM queries
```python
# Get single widget (raises error if not found)
btn = self.query_one("#my-btn", Button)

# Get all matching widgets
for label in self.query(Label):
    label.update("new text")
```

### Workers (background tasks)
```python
from textual.worker import Worker
from textual import work

@work(exclusive=True)
async def fetch_data(self) -> None:
    result = await some_async_call()
    self.data = result  # triggers reactive watcher
```

### Screens
```python
from textual.screen import Screen

class HelpScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Close")]
    def compose(self) -> ComposeResult:
        yield Static("Help content here")

# Push from app:
self.app.push_screen(HelpScreen())
# Pop:
self.app.pop_screen()
```

---

## ❌ Common Mistakes to Avoid

1. **Using `print()` inside a Textual app** — it corrupts the TUI. Use `self.log(...)` or `RichLog` widget instead.
2. **Calling `compose()` manually** — Textual calls it internally. Never call it yourself.
3. **Blocking the event loop** — use `async def` + `await`, or use `@work` for CPU-heavy tasks.
4. **Wrong import path** — containers are in `textual.containers`, not `textual.widgets`.
5. **CSS class names** — TCSS uses `.class-name` (with dot), IDs use `#id` (with hash). Case-sensitive.
6. **`on_` handler name format** — must match `on_<WidgetClass>_<message_name>`, e.g. `on_button_pressed`. Underscores replace dots and CamelCase → snake_case.
7. **`TextArea` vs `Input`** — `Input` is single-line; `TextArea` is multi-line. Don't confuse them.
8. **Running `app.run()` inside `async` context** — call `app.run()` from a plain `if __name__ == "__main__"` block, or use `await app.run_async()` inside async code.

---

## Dev Workflow

```bash
# Live reload during development
textual run --dev my_app.py

# Open devtools console (in a separate terminal while app runs)
textual console

# Preview CSS changes without restarting
# (use `textual run --dev` — saves reload on every file change)
```

> `textual-dev` package provides the `textual` CLI. Install separately: `pip install textual-dev`

---

## Reference Files

Read these for deeper coverage:

- **[references/api-patterns.md](references/api-patterns.md)** — Lifecycle, reactivity, compose, workers, screens, DOM queries, BINDINGS
- **[references/events-messages.md](references/events-messages.md)** — All events, custom messages, bubbling, `@on` decorator
- **[references/layout-css.md](references/layout-css.md)** — TCSS layout system, containers, grid, dock, sizing units
- **[references/widgets-reference.md](references/widgets-reference.md)** — Key widget APIs, constructor signatures, messages emitted

---

## Official Docs

- Guide: https://textual.textualize.io/guide/
- Widget Gallery: https://textual.textualize.io/widget_gallery/
- API Reference: https://textual.textualize.io/api/
- Tutorial (full stopwatch app): https://textual.textualize.io/tutorial/
