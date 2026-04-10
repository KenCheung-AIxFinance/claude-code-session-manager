# Textual API Patterns Reference

## App Lifecycle

```
on_load()        → before DOM is built (read config here)
on_mount()       → after DOM is ready (start workers, fetch data)
on_ready()       → after first frame rendered
```

```python
class MyApp(App):
    def on_load(self) -> None:
        # Early setup, no widgets yet
        pass

    def on_mount(self) -> None:
        # Widgets are ready, safe to query
        self.query_one(Input).focus()
```

## compose() Rules

- Always a generator (`yield` not `return`)
- Return type is `ComposeResult`
- Use context managers for containers:

```python
def compose(self) -> ComposeResult:
    yield Header()
    with Horizontal():
        yield Button("OK", id="ok")
        yield Button("Cancel", id="cancel")
    yield Footer()
```

- Nested custom widgets:

```python
class Sidebar(Widget):
    def compose(self) -> ComposeResult:
        yield Label("Sidebar")
        yield Button("Action")

class MyApp(App):
    def compose(self) -> ComposeResult:
        yield Sidebar()
        yield MainContent()
```

## BINDINGS

```python
from textual.app import App
from textual.binding import Binding

class MyApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark"),
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("f1", "push_screen('help')", "Help"),
    ]

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_save(self) -> None:
        self.notify("Saved!")
```

Actions prefixed with `app.` target the App; otherwise they target the focused widget.

## reactive

```python
from textual.reactive import reactive

class Counter(Widget):
    # Simple reactive
    count: reactive[int] = reactive(0)

    # With init=False: don't trigger watcher on init
    name: reactive[str] = reactive("", init=False)

    # With repaint=True: repaint widget when changed (default True)
    # With layout=True: re-layout widget when changed
    size: reactive[int] = reactive(10, layout=True)

    def watch_count(self, new_value: int) -> None:
        """Called whenever count changes."""
        self.update(f"Count: {new_value}")

    def watch_name(self, old: str, new: str) -> None:
        """Optionally receive old and new values."""
        pass

    def compute_display_count(self) -> str:
        """Computed reactive — no setter, derived from other state."""
        return f"#{self.count}"
```

## DOM Queries

```python
# Single widget by ID — raises NoMatches if not found
btn = self.query_one("#submit", Button)

# Single widget by type
input_box = self.query_one(Input)

# All matching — returns DOMQuery (iterable)
for widget in self.query(".item"):
    widget.add_class("selected")

# Scoped query (search within a widget's subtree)
sidebar = self.query_one("#sidebar")
items = sidebar.query(Label)

# Safe single match (returns None if not found) — use try/except instead:
try:
    w = self.query_one("#maybe-missing", Label)
except NoMatches:
    w = None
```

## Mount / Unmount Widgets Dynamically

```python
# Mount new widgets
await self.mount(Button("New button"))

# Mount at specific position
await self.mount(Label("Top"), before=self.query_one("#existing"))

# Remove a widget
widget.remove()

# Remove all children
self.query(".item").remove()
```

## Workers (Background Tasks)

```python
from textual import work
from textual.worker import Worker, WorkerState

class MyApp(App):
    @work(exclusive=True, thread=False)  # async worker
    async def load_data(self) -> None:
        data = await fetch_something()
        self.results = data  # safe: Textual is thread-safe for reactive

    @work(thread=True)  # run in thread pool (for blocking/CPU code)
    def process_file(self, path: str) -> str:
        return heavy_computation(path)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            self.log(f"Worker done: {event.worker.result}")
```

`exclusive=True` cancels any running worker of the same method before starting a new one.

## Screens

```python
from textual.screen import Screen, ModalScreen

# Regular screen — replaces current screen
class SettingsScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Label("Settings")

# Modal screen — overlays on top
class ConfirmDialog(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Are you sure?")
            yield Button("Yes", id="yes")
            yield Button("No", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

# Usage:
self.app.push_screen(SettingsScreen())
self.app.push_screen(ConfirmDialog(), callback=self.handle_result)

# Switch (replace entire stack):
self.app.switch_screen(NewScreen())

async def handle_result(self, confirmed: bool) -> None:
    if confirmed:
        await self.delete_item()
```

## Notifications (Toast)

```python
self.notify("Operation complete!")
self.notify("Something went wrong", severity="error")
self.notify("Heads up", severity="warning", timeout=5.0)
```

## update() vs refresh()

```python
# For Static/Label: update content
self.query_one("#status", Static).update("New content [bold]bold[/bold]")

# Force re-render (rarely needed)
widget.refresh()
```

## Timers

```python
def on_mount(self) -> None:
    self.set_interval(1.0, self.tick)   # every second
    self.set_timer(5.0, self.delayed)   # once after 5s

def tick(self) -> None:
    self.count += 1   # triggers reactive watcher
```

## App Dark Mode

```python
self.dark = True   # switch to dark theme
self.dark = False  # switch to light theme
# Toggle:
self.action_toggle_dark()  # built-in action
```

## CSS — Inline vs External

```python
# Inline (CSS class variable)
class MyApp(App):
    CSS = """
    Button {
        margin: 1 2;
        background: $accent;
    }
    """

# External file
class MyApp(App):
    CSS_PATH = "my_app.tcss"
```

Both `CSS` and `CSS_PATH` can coexist. Class variables on widget subclasses also work:

```python
class MyWidget(Widget):
    DEFAULT_CSS = """
    MyWidget {
        height: auto;
        padding: 1;
    }
    """
```
