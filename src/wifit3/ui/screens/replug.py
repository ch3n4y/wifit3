"""Wait-for-user-to-replug modal (Linux)."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, LoadingIndicator

_UNPLUG = ("已为 [bold]{name}[/] 安装访问权限。\n"
           "需要重新插拔以刷新网卡状态。\n\n"
           "等待你 [bold $text-warning]现在拔出网卡…[/]")
_REPLUG = ("[bold $text-success]网卡已拔出 ✓[/]\n\n"
           "等待你 [bold $text-warning]重新插入…[/]")


class ReplugModal(ModalScreen[str]):
    """Watches for an unplug→replug via the injected presence-waiter (no device-manager handle, so
    it never drives a bus rescan itself). Dismisses "replugged" / "skip" / "timeout"."""

    BINDINGS = [Binding("escape", "skip", "跳过", show=True)]

    DEFAULT_CSS = """
    ReplugModal { align: center middle; }
    ReplugModal #dialog {
        width: 64; max-width: 90%; height: auto;
        border: thick $primary; background: $surface; padding: 1 2;
    }
    ReplugModal #title { width: 1fr; text-align: center; text-style: bold; margin-bottom: 1; }
    ReplugModal #status { width: 1fr; text-align: center; margin-bottom: 1; }
    ReplugModal #spin { height: 1; margin-bottom: 1; }
    ReplugModal #button-row { height: auto; align: center middle; }
    ReplugModal #btn-skip { background: $primary; color: auto; }
    """

    def __init__(self, name: str, wait_present) -> None:
        super().__init__()
        self._name = name
        self._wait_present = wait_present   # async (present: bool) -> bool
        self._done = False

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("[bold $text-warning]需要重新插拔[/]", id="title")
            yield Label(_UNPLUG.format(name=self._name), id="status")
            with Center(id="spin"):
                yield LoadingIndicator()
            with Horizontal(id="button-row"):
                yield Button("跳过", id="btn-skip")

    def on_mount(self) -> None:
        self.run_worker(self._watch(), exclusive=True)

    async def _watch(self) -> None:
        gone = await self._wait_present(False)
        if self._done:
            return
        if not gone:
            self._finish("timeout")
            return
        self.query_one("#status", Label).update(_REPLUG)
        back = await self._wait_present(True)
        if self._done:
            return
        self._finish("replugged" if back else "timeout")

    def _finish(self, result: str) -> None:
        if self._done:
            return
        self._done = True
        self.dismiss(result)          # removing the screen cancels the still-waiting worker

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self._finish("skip")

    def action_skip(self) -> None:
        self._finish("skip")
