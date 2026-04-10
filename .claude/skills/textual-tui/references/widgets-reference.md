# Textual Widget API Reference

## Button

```python
from textual.widgets import Button

Button("Label", id="btn-id", variant="default")
# variant: "default" | "primary" | "success" | "warning" | "error"

# Messages:
# Button.Pressed → event.button
```

## Input

```python
from textual.widgets import Input

Input(
    placeholder="Enter text...",
    id="my-input",
    password=False,       # show/hide text
    value="initial",      # initial value
)

# Get value:
val = self.query_one(Input).value

# Set value:
self.query_one(Input).value = "new text"

# Messages:
# Input.Changed  → event.value
# Input.Submitted → event.value  (Enter key)
```

## TextArea

```python
from textual.widgets import TextArea

TextArea(
    "initial text",
    language="python",  # syntax highlighting: "python","markdown","sql","json",etc
    id="editor",
    read_only=False,
)

# Get/set content:
ta = self.query_one(TextArea)
content = ta.text
ta.load_text("new content")

# Requires: pip install "textual[syntax]" for syntax highlighting
```

## Static / Label

```python
from textual.widgets import Static, Label

# Static renders Rich markup:
Static("[bold]Hello[/bold] [green]World[/green]")

# Update content:
widget.update("New content with [italic]markup[/italic]")

# Label is alias for Static with slightly different defaults
```

## DataTable

```python
from textual.widgets import DataTable

table = DataTable()
table.add_columns("Name", "Age", "City")
table.add_row("Alice", 30, "HK")
table.add_row("Bob", 25, "NY")

# With row keys:
key = table.add_row("Charlie", 35, "UK")

# Styled rows:
table.add_row("Error", "❌", style="red")

# Access cell by coordinate:
value = table.get_cell_at(Coordinate(0, 0))

# Messages:
# DataTable.RowSelected → event.row_key, event.cursor_row
# DataTable.CellSelected → event.value, event.coordinate

# Show cursor:
table.cursor_type = "row"  # "cell" | "row" | "column" | "none"
```

## Select (Dropdown)

```python
from textual.widgets import Select

Select(
    [("Option A", "a"), ("Option B", "b")],
    id="my-select",
    prompt="Choose...",
    value="a",  # initial selection
)

# Get value:
val = self.query_one(Select).value  # returns Select.BLANK if none

# Messages:
# Select.Changed → event.value (or Select.BLANK)
```

## Checkbox / Switch

```python
from textual.widgets import Checkbox, Switch

Checkbox("Enable feature", id="cb", value=True)
Switch(id="sw", value=False)

# Get state:
checked = self.query_one(Checkbox).value  # bool

# Messages:
# Checkbox.Changed → event.value (bool)
# Switch.Changed → event.value (bool)
```

## RadioButton / RadioSet

```python
from textual.widgets import RadioButton, RadioSet

with RadioSet(id="choice"):
    yield RadioButton("Option A", id="opt-a")
    yield RadioButton("Option B", id="opt-b", value=True)  # pre-selected

# Messages:
# RadioSet.Changed → event.pressed (RadioButton widget)
# event.index — index of selected option
```

## ProgressBar

```python
from textual.widgets import ProgressBar

bar = ProgressBar(total=100, show_bar=True, show_percentage=True)

# Update:
bar.advance(10)          # increment by 10
bar.progress = 50        # set absolute value
bar.update(total=200)    # change total
```

## RichLog (scrollable log)

```python
from textual.widgets import RichLog

log = RichLog(id="log", highlight=True, markup=True)

# Write messages:
log.write("Plain text")
log.write("[green]Success![/green]")
log.write({"key": "value"})  # Rich pretty-prints dicts/lists
log.clear()
```

## Log (simple append-only log)

```python
from textual.widgets import Log

log = Log(id="log")
log.write_line("message")
log.clear()
```

## Tree

```python
from textual.widgets import Tree

tree = Tree("Root", id="tree")
root = tree.root
branch = root.add("Branch 1")
branch.add_leaf("Leaf A")
branch.add_leaf("Leaf B")
root.add("Branch 2").add_leaf("Leaf C")

tree.root.expand()  # expand all

# Messages:
# Tree.NodeSelected → event.node
# event.node.data — attached data
# event.node.label — node label text
# Tree.NodeExpanded, Tree.NodeCollapsed
```

## DirectoryTree

```python
from textual.widgets import DirectoryTree
from pathlib import Path

tree = DirectoryTree(Path("/home/user"), id="files")

# Messages:
# DirectoryTree.FileSelected → event.path (Path)
# DirectoryTree.DirectorySelected → event.path (Path)
```

## TabbedContent

```python
from textual.widgets import TabbedContent, TabPane

with TabbedContent(id="tabs"):
    with TabPane("Tab 1", id="tab1"):
        yield Static("Content 1")
    with TabPane("Tab 2", id="tab2"):
        yield Static("Content 2")

# Switch tab:
self.query_one(TabbedContent).active = "tab2"

# Messages:
# TabbedContent.TabActivated → event.pane, event.tab
```

## Collapsible

```python
from textual.widgets import Collapsible

with Collapsible(title="Details", collapsed=True):
    yield Static("Hidden content")
    yield Button("Action")
```

## ListView / ListItem

```python
from textual.widgets import ListView, ListItem, Label

with ListView(id="list"):
    yield ListItem(Label("Item 1"), id="item-1")
    yield ListItem(Label("Item 2"), id="item-2")

# Dynamically add:
await list_view.append(ListItem(Label("Item 3")))

# Messages:
# ListView.Selected → event.item (ListItem), event.list_view
```

## OptionList

```python
from textual.widgets import OptionList
from textual.widgets.option_list import Option, Separator

list_widget = OptionList(
    "Option A",
    "Option B",
    Separator(),
    Option("Option C (disabled)", disabled=True),
)

# Get selected:
idx = list_widget.highlighted  # int or None

# Messages:
# OptionList.OptionSelected → event.option, event.option_index
```

## Header / Footer

```python
from textual.widgets import Header, Footer

# Header shows app title and clock
Header(show_clock=True)

# Footer shows BINDINGS key hints
Footer()
```

## Markdown

```python
from textual.widgets import Markdown, MarkdownViewer

# Render markdown:
Markdown("# Hello\n\nThis is **markdown**.")

# Update:
md = self.query_one(Markdown)
await md.update("# New content")

# MarkdownViewer adds table of contents + scrolling:
MarkdownViewer(markdown_text, show_table_of_contents=True)
```

## Toast (notifications)

```python
# Programmatic notifications (not a widget you compose):
self.notify("Message", severity="information")  # default
self.notify("Error occurred", severity="error", timeout=5.0)
self.notify("Warning", severity="warning")
# severity: "information" | "warning" | "error"
```

## Custom Widget

```python
from textual.widget import Widget
from textual.reactive import reactive

class MyWidget(Widget):
    DEFAULT_CSS = """
    MyWidget {
        height: auto;
        border: solid $accent;
        padding: 1;
    }
    """

    value: reactive[str] = reactive("")

    def __init__(self, initial: str = "", **kwargs):
        super().__init__(**kwargs)
        self.value = initial

    def compose(self) -> ComposeResult:
        yield Label(self.value, id="content")

    def watch_value(self, new_val: str) -> None:
        try:
            self.query_one("#content", Label).update(new_val)
        except Exception:
            pass  # widget not yet mounted

    def render(self) -> str:
        # Alternative: override render() instead of compose()
        # for simple text-only widgets
        return f"Value: {self.value}"
```

Use `compose()` for complex widgets with child widgets; use `render()` for simple text output.
