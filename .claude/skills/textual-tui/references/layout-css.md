# Textual Layout & CSS (TCSS) Reference

## TCSS Basics

Textual CSS (TCSS) is a subset of CSS adapted for terminal cells (not pixels).

**Units:**
- `1` = 1 terminal cell (character width/height)
- `1fr` = fractional unit (distribute remaining space)
- `50%` = 50% of parent's dimension
- `auto` = fit to content

**Colors:**
- Named: `red`, `blue`, `green`, `white`, `black`
- Theme vars: `$primary`, `$secondary`, `$accent`, `$background`, `$surface`, `$panel`, `$boost`, `$text`, `$text-muted`, `$error`, `$warning`, `$success`
- Hex: `#ff0000`
- RGB: `rgb(255, 0, 0)`

## Display Layouts

### Vertical (default)
```css
Screen {
    layout: vertical;  /* default */
}
```

### Horizontal
```css
#toolbar {
    layout: horizontal;
    height: 3;
}
```

### Grid
```css
#grid-container {
    layout: grid;
    grid-size: 3 2;       /* 3 columns, 2 rows */
    grid-columns: 1fr 2fr 1fr;
    grid-rows: auto;
    grid-gutter: 1;
}
```

## Dock

Docks a widget to an edge, outside the normal flow:

```css
Header {
    dock: top;
}

Footer {
    dock: bottom;
}

#sidebar {
    dock: left;
    width: 20;
}
```

## Sizing

```css
Widget {
    width: 50%;       /* percent of parent */
    width: 1fr;       /* fractional */
    width: 20;        /* fixed cells */
    width: auto;      /* fit content */

    height: 10;
    height: 100%;
    height: auto;

    min-width: 10;
    max-width: 40;
    min-height: 3;
    max-height: 20;
}
```

## Margin & Padding

```css
/* TRBL shorthand (top right bottom left) */
Widget {
    margin: 1 2;       /* top/bottom=1, left/right=2 */
    margin: 1 2 1 2;
    padding: 0 1;
}
```

## Border

```css
Widget {
    border: solid $accent;
    border: round $primary;
    border: heavy white;
    border: none;
    /* Types: ascii, blank, dashed, double, heavy, hidden, hkey, inner,
              none, outer, panel, round, solid, tall, thick, vkey, wide */
}
```

Border title/subtitle (label on border):
```python
widget.border_title = "My Widget"
widget.border_subtitle = "Press Q to close"
```

## Common Layout Patterns

### Two-column layout (sidebar + main)
```python
def compose(self) -> ComposeResult:
    with Horizontal():
        yield Sidebar()
        yield MainContent()
```
```css
Sidebar {
    width: 25%;
    height: 100%;
}
MainContent {
    width: 1fr;
    height: 100%;
}
```

### Header + scrollable content + footer
```python
def compose(self) -> ComposeResult:
    yield Header()
    with ScrollableContainer(id="content"):
        yield LongContent()
    yield Footer()
```
```css
#content {
    height: 1fr;  /* fill remaining space */
}
```

### Centered dialog
```python
from textual.containers import Center, Middle

def compose(self) -> ComposeResult:
    with Center():
        with Middle():
            yield Static("Centered content", id="dialog")
```

### Grid of cards
```python
def compose(self) -> ComposeResult:
    with Grid(id="cards"):
        for item in self.items:
            yield Card(item)
```
```css
#cards {
    layout: grid;
    grid-size: 3;
    grid-gutter: 1 2;
    grid-columns: 1fr 1fr 1fr;
}
```

## Pseudo-classes

```css
Button:hover {
    background: $accent;
}

Button:focus {
    border: solid $primary;
}

Button.-active {
    background: $success;
}

Input:focus {
    border: solid $accent;
}
```

## Adding/Removing Classes

```python
widget.add_class("selected")
widget.remove_class("selected")
widget.toggle_class("selected")

# Via CSS query
self.query(".item").add_class("highlight")
```

## Visibility & Display

```css
/* Hide but keep layout space */
Widget {
    visibility: hidden;
}

/* Remove from layout entirely */
Widget {
    display: none;
}
```

```python
# Python equivalents:
widget.display = False     # same as display: none
widget.visible = False     # same as visibility: hidden
```

## Overflow / Scrolling

```css
Widget {
    overflow: auto;     /* scroll when content overflows */
    overflow: hidden;   /* clip content */
    overflow-x: auto;
    overflow-y: scroll;
}
```

## Align / Content Alignment

```css
Widget {
    align: center middle;   /* horizontal vertical */
    content-align: center middle;
    text-align: center;
}
```

## Layer System

For overlapping widgets:
```css
Screen {
    layers: base overlay;
}

#base-content {
    layer: base;
}

#modal-overlay {
    layer: overlay;
}
```

## Inline Styles (Python)

```python
widget.styles.background = "blue"
widget.styles.width = "50%"
widget.styles.height = "auto"
widget.styles.padding = (1, 2)  # top/bottom, left/right
widget.styles.border = ("solid", "white")
```

## Containers Import

Always import containers from `textual.containers`:

```python
from textual.containers import (
    Horizontal,
    Vertical,
    ScrollableContainer,
    Center,
    Middle,
    Grid,
    Container,
)
```

**Not** from `textual.widgets`.
