"""WinUSB install confirmation: a visual-guide modal.

Shown when the user STARTs a supported card that isn't WinUSB-bound yet. It draws the
Wifit3 ↔ WinUSB ↔ card chain with the WinUSB link flagged as the missing REQUIRED piece
(a pulsing red badge), explains the reversible driver swap, and asks to install. Dismisses
with ``True`` (install) / ``False`` (cancel). Copy is kept plain for non-native English
readers.
"""
from __future__ import annotations

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

# Red shades cycled to make the REQUIRED badge pulse (ping-pong for a smooth throb).
_PULSE = ["#6e0000", "#8a0000", "#a40000", "#c00000", "#a40000", "#8a0000"]

# Default copy = the Windows WinUSB case. The Linux connect-failure path reuses this same
# dialog (a missing REQUIRED link between Wifit3 and the card) with its own wording, so the
# diagram/title/warning/verb are parametrised rather than the dialog forked.
_DEFAULT_TITLE = "Wifit3 需要 WinUSB 驱动才能与此网卡通信"
_DEFAULT_WARNING = (
    "[bold $text-warning]警告：[/]这会[italic $text-warning]替换网卡当前驱动[/]"
    "\n\n"
    "Windows 将不再把它识别为无线网卡。\n\n"
    "可点按 [bold white on red] x [/] 按钮卸载 WinUSB")


class ConfirmInstallDialog(ModalScreen[bool]):
    BINDINGS = [
        Binding("y", "yes", "安装", show=True),
        Binding("n", "no", "取消", show=True),
        Binding("escape", "no", "取消", show=True),
    ]

    DEFAULT_CSS = """
    ConfirmInstallDialog { align: center middle; }
    ConfirmInstallDialog #dialog {
        width: auto; max-width: 96%; height: auto;
        border: thick $primary; background: $surface; padding: 1 2;
    }
    ConfirmInstallDialog #title {
        width: 1fr; text-align: center; margin-bottom: 1; text-style: bold;
    }
    ConfirmInstallDialog #diagram { content-align: center middle; margin-bottom: 1; }
    ConfirmInstallDialog #warn { width: auto; text-align: left; }
    ConfirmInstallDialog #warn-center { width: 1fr; height: auto; margin-bottom: 1; }
    ConfirmInstallDialog #question {
        width: 1fr; text-align: center; margin-bottom: 1; text-style: bold;
    }
    ConfirmInstallDialog #button-row { height: auto; align: center middle; }
    ConfirmInstallDialog #button-row Button { margin: 0 2; }
    """

    def __init__(self, description: str, *, chipset: str | None = None,
                 title: str = _DEFAULT_TITLE,
                 link_label: str = "WinUSB 驱动", warning: str = _DEFAULT_WARNING,
                 verb: str = "为以下网卡安装 WinUSB", confirm_label: str = "安装",
                 also: str = "") -> None:
        super().__init__()
        self._full = description
        self._also = also          # appended inside the question's bold (e.g. " (+ 119 cards)")
        # Short name for the diagram box (the chipset, capped so a long name doesn't blow out the
        # box width). Prefer the structured chipset; fall back to the description's head.
        self._short = (chipset or description.split("(")[0].strip())[:18]
        self._pulse_i = 0
        self._title = title
        self._link_label = link_label   # middle (REQUIRED) box: "WinUSB Driver" / "udev + modprobe"
        self._warning = warning
        self._verb = verb               # question stem before the card name
        self._confirm_label = confirm_label

    def _diagram(self, pulse: str) -> Table:
        """The Wifit3 ◄──► WinUSB ◄──► card chain + status row, as a Rich grid (Rich handles
        the column alignment so the ✓/✗ land under their boxes). ``pulse`` is the REQUIRED
        badge's current background red."""
        grid = Table.grid(padding=(0, 1))
        for _ in range(5):
            grid.add_column(justify="center", vertical="middle")
        grid.add_row(
            Panel("Wifit3", border_style="green", expand=False, padding=(0, 1)),
            Text("◄──►", style="bold"),
            Panel(self._link_label, border_style="red", expand=False, padding=(0, 1)),
            Text("◄──►", style="bold"),
            Panel(self._short, border_style="green", expand=False, padding=(0, 1)),
        )
        grid.add_row(
            Text("✓", style="bold green"),
            Text(""),
            Text(" ✗ 必需 ", style=f"bold white on {pulse}"),
            Text(""),
            Text("✓ 已支持", style="bold green"),
        )
        return grid

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._title, id="title")
            yield Static(self._diagram(_PULSE[0]), id="diagram")
            with Center(id="warn-center"):
                yield Label(self._warning, id="warn")
            yield Label(f"{self._verb} [bold]{self._full}{self._also}[/]？", id="question")
            with Horizontal(id="button-row"):
                yield Button(self._confirm_label, variant="success", id="btn-yes")
                yield Button("取消", variant="default", id="btn-no")

    def on_mount(self) -> None:
        self.query_one("#btn-yes", Button).focus()
        # Pulse the REQUIRED badge. The diagram is a small grid; re-rendering it per tick is
        # cheap, and it's only alive while the modal is open.
        self.set_interval(0.16, self._pulse)

    def _pulse(self) -> None:
        self._pulse_i = (self._pulse_i + 1) % len(_PULSE)
        self.query_one("#diagram", Static).update(self._diagram(_PULSE[self._pulse_i]))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-yes")

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)
