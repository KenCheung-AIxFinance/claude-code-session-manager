# Textual Events & Messages Reference

## Event Handler Naming Convention

Method name: `on_<WidgetClassName>_<message_name>`  
Where:
- `WidgetClassName` → snake_case of the widget class
- `message_name` → snake_case of the message class

Examples:
| Widget.Message | Handler method name |
|---|---|
| `Button.Pressed` | `on_button_pressed` |
| `Input.Changed` | `on_input_changed` |
| `Input.Submitted` | `on_input_submitted` |
| `Select.Changed` | `on_select_changed` |
| `DataTable.RowSelected` | `on_data_table_row_selected` |
| `Switch.Changed` | `on_switch_changed` |
| `Checkbox.Changed` | `on_checkbox_changed` |
| `TabbedContent.TabActivated` | `on_tabbed_content_tab_activated` |
| `ListView.Selected` | `on_list_view_selected` |

## @on Decorator (Preferred)

```python
from textual import on
from textual.widgets import Button, Input

class MyApp(App):
    def compose(self) -> ComposeResult:
        yield Button("Save", id="save")
        yield Button("Cancel", id="cancel")
        yield Input(placeholder="Name", id="name-input")

    @on(Button.Pressed, "#save")
    def save_pressed(self, event: Button.Pressed) -> None:
        self.save()

    @on(Button.Pressed, "#cancel")
    def cancel_pressed(self) -> None:  # event arg is optional
        self.exit()

    @on(Input.Changed, "#name-input")
    def name_changed(self, event: Input.Changed) -> None:
        self.title = event.value
```

CSS selectors in `@on` are matched against the event's sender widget.

## Common Widget Messages

### Button
```python
event: Button.Pressed
event.button        # the Button widget
event.button.id     # button's id
```

### Input
```python
event: Input.Changed
event.value         # current string value
event.input         # the Input widget

event: Input.Submitted
event.value         # submitted string
```

### Select
```python
event: Select.Changed
event.value         # selected value (or Select.BLANK)
event.select        # the Select widget
```

### Switch / Checkbox
```python
event: Switch.Changed
event.value         # bool
event.switch

event: Checkbox.Changed
event.value         # bool
```

### DataTable
```python
event: DataTable.RowSelected
event.row_key       # RowKey
event.cursor_row    # int row index

event: DataTable.CellSelected
event.cell_key      # CellKey
event.value         # cell value
event.coordinate    # Coordinate(row, column)
```

### ListView
```python
event: ListView.Selected
event.item          # the ListItem widget
event.list_view     # the ListView widget
```

### TabbedContent
```python
event: TabbedContent.TabActivated
event.tab           # Tab widget
event.pane          # TabPane widget
```

### Tree
```python
event: Tree.NodeSelected
event.node          # TreeNode
event.node.data     # attached data

event: Tree.NodeExpanded
event.node
```

## System Events

These come from the framework, not widgets:

```python
def on_key(self, event: events.Key) -> None:
    if event.key == "ctrl+c":
        self.exit()
    self.log(f"Key: {event.character}, name: {event.key}")

def on_mount(self) -> None:
    pass  # after DOM ready

def on_resize(self, event: events.Resize) -> None:
    self.log(f"Size: {event.size}")

def on_focus(self, event: events.Focus) -> None:
    pass  # widget received focus

def on_blur(self, event: events.Blur) -> None:
    pass  # widget lost focus

def on_click(self, event: events.Click) -> None:
    self.log(f"Click at {event.x},{event.y}")
```

## Custom Messages

```python
from textual.message import Message

class MyWidget(Widget):
    class DataReady(Message):
        """Emitted when data is loaded."""
        def __init__(self, data: list) -> None:
            super().__init__()
            self.data = data

    def load(self) -> None:
        data = fetch()
        self.post_message(self.DataReady(data))

# Handle in parent:
class MyApp(App):
    @on(MyWidget.DataReady)
    def data_ready(self, event: MyWidget.DataReady) -> None:
        self.process(event.data)
```

## Message Bubbling

Messages bubble up the DOM by default. Set `bubble = False` on a message class to stop it:

```python
class MyWidget(Widget):
    class LocalEvent(Message, bubble=False):
        pass
```

Stop bubbling on a specific event instance:
```python
def on_button_pressed(self, event: Button.Pressed) -> None:
    event.stop()  # don't propagate further
```

## Preventing Default Behaviors

Some events have default behaviors (e.g., `Input.Submitted` clears focus).

```python
def on_input_submitted(self, event: Input.Submitted) -> None:
    event.prevent_default()  # stop default behavior
    self.process(event.value)
```
