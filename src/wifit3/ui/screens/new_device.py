"""New-device prompt: a supported card was plugged in mid-session; offer to bring it up + merge it
into the pool. Friendly (primary-colored, not an error), Yes/No, dismisses a bool."""
from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class NewDeviceDialog(ModalScreen[bool]):
    """Prompt shown when the app's device listener spots a new openable card. Dismisses True (bring it
    up) or False (leave it). Escape declines."""

    BINDINGS = [Binding("escape", "decline", "暂不", show=True)]

    DEFAULT_CSS = """
    NewDeviceDialog { align: center middle; }
    NewDeviceDialog #dialog {
        width: 64; max-width: 90%; height: auto;
        border: thick $primary; background: $surface; padding: 1 2;
    }
    NewDeviceDialog #title { width: 1fr; text-align: center; text-style: bold;
                             color: $text-success; margin-bottom: 1; }
    NewDeviceDialog #desc { width: 1fr; text-align: center; text-style: bold; margin-bottom: 1; }
    NewDeviceDialog #prompt { width: 1fr; text-align: center; margin-bottom: 1; }
    NewDeviceDialog #button-row { height: auto; align: center middle; }
    NewDeviceDialog #button-row Button { margin: 0 1; }
    """

    def __init__(self, description: str) -> None:
        super().__init__()
        self._description = description

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("检测到新的无线设备", id="title")
            yield Static(self._description, id="desc")
            yield Static("是否初始化此设备？", id="prompt")
            with Horizontal(id="button-row"):
                yield Button("是", variant="success", id="btn-yes")
                yield Button("否", variant="default", id="btn-no")

    @on(Button.Pressed, "#btn-yes")
    def _yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-no")
    def _no(self) -> None:
        self.dismiss(False)

    def action_decline(self) -> None:
        self.dismiss(False)
