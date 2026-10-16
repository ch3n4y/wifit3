from __future__ import annotations

import asyncio
import logging
import subprocess
import os

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich.markup import escape
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalGroup
from textual.events import Event
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select

from wifit3.campaigns.pin import EMPTY_PIN_LABEL
from wifit3.models import CaptureType, PersistedCapture
from wifit3.ui.vault.tools_ui import UI_TOOLS


logger = logging.getLogger(__name__)


def _hex_to_ascii(hex_key: Optional[str]) -> str:
    if not hex_key:
        return ""
    try:
        raw = bytes.fromhex(hex_key)
    except ValueError:
        return ""
    return raw.decode("ascii") if all(32 <= b < 127 for b in raw) else ""


def relative_time(timestamp: int) -> str:
    diff = int(datetime.now().timestamp() - timestamp)
    if diff < 60: return    f"{diff}秒前"
    if diff < 3600: return  f"{diff // 60}分钟前"
    if diff < 86400: return f"{diff // 3600}小时前"
    return                  f"{diff // 86400}天前"


class ConfirmModal(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "cancel", "取消")]
    DEFAULT_CSS = """
    ConfirmModal { align: center middle; }
    ConfirmModal #dialog { width: 54; height: auto; border: thick $primary; background: $surface; padding: 1 2; }
    ConfirmModal #prompt { margin-bottom: 1; }
    ConfirmModal Horizontal { align: right middle; height: auto; }
    ConfirmModal Button { margin-left: 1; }
    """
    def __init__(self, prompt: str) -> None:
        super().__init__()
        self._prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(Text.from_markup(self._prompt), id="prompt")
            with Horizontal():
                yield Button(Text("否"), "default", id="no")
                yield Button(Text("是"), "error", id="yes")

    @on(Button.Pressed, "#yes")
    def _yes(self, event: Event) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#no")
    def _no(self, event: Event) -> None:
        self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class _CapturePanel(VerticalGroup):
    DEFAULT_CSS = """
    _CapturePanel {
        background: $surface;
        max-width: 81;
        border: round $primary; padding: 0 1;
        margin-top: 1;
    }
    _CapturePanel .file { margin-bottom: 1; }
    _CapturePanel .date { height: 1; margin-bottom: 1; }
    _CapturePanel .key-row { height: 1; align: left middle; margin-bottom: 1; }
    _CapturePanel .key-display { height: 1; margin-right: 3; margin-bottom: 1; }
    _CapturePanel .copy-btn { min-width: 0; margin-right: 3; }
    _CapturePanel .verify-btn { min-width: 14; }
    _CapturePanel .actions { height: auto; align: left middle; }
    _CapturePanel .spacer { width: 1fr; }
    """

    def __init__(self, title: str, captures: List[PersistedCapture],
                 cracked_key: Optional[str] = None) -> None:
        super().__init__()
        self._title = title
        self._cracked_key = cracked_key
        self._by_path: Dict[str, PersistedCapture] = {}
        for cap in sorted(captures, key=lambda c: c.timestamp, reverse=True):
            self._by_path.setdefault(cap.path, cap)
        self._files = list(self._by_path.values())
        self._verify_task: Optional[asyncio.Task] = None

    def cancel_verification(self) -> None:
        """Cancel any running verification task on this panel."""
        if self._verify_task is not None and not self._verify_task.done():
            self._verify_task.cancel()
            self._verify_task = None

    def compose(self) -> ComposeResult:
        n = len(self._files)
        if self._title == "WPS PSKs":
            self.border_title = f"WPS（{n} 个 PSK）"
        elif self._title == "WPA PSKs":
            self.border_title = f"WPA（{n} 个 PSK）"
        elif self._title == "WPS PINs":
            self.border_title = f"WPS（{n} 个 PIN）"
        elif self._title == "WEP KEYs":
            self.border_title = f"WEP（{n} 个密钥）"
        elif self._title == "HASHCAT":
            self.border_title = f"HASHCAT（{n} 个 .hc22000 文件）"
        elif self._title == "HANDSHAKE":
            self.border_title = f"握手（{n} 个 .pcap 文件）"
        else:
            self.border_title = f"{self._title}（{n}）"

        newest = self._files[0]
        yield Select([(Path(c.path).name, c.path) for c in self._files], value=newest.path, allow_blank=False, classes="file")

        # Display Key or Summary
        with VerticalGroup(classes="key-group"):
            pass # populated on file_changed

        yield Label(self._date_markup(newest), classes="date")

        with Horizontal(classes="actions"):
            yield Button("打开目录", classes="open-dir")
            yield Label("", classes="spacer")
            yield Button("删除", "error", classes="delete")

    def on_mount(self) -> None:
        self._update_display(self._files[0])

    def _date_markup(self, cap: PersistedCapture) -> str:
        dt = datetime.fromtimestamp(cap.timestamp).strftime("%Y-%m-%d %H:%M")
        return f"[dim]修改于：[/] {dt} [dim]({relative_time(cap.timestamp)})[/dim]"

    def _update_display(self, cap: PersistedCapture) -> None:
        self.query_one(".date", Label).update(self._date_markup(cap))

        kg = self.query_one(".key-group")
        kg.remove_children()
        
        actions = self.query_one(".actions")
        for btn in actions.query(".tool-btn"):
            btn.remove()
            
        for tool in self.app.vault.manager.tools.values():
            if tool.can_crack(cap):
                btn = Button(f"启动 {tool.name}", "primary", classes=f"tool-btn launch-tool-{tool.name}")
                actions.mount(btn, before=".spacer")

        def _row(label: str, val: str, btn_id: str, target_type: Optional[CaptureType] = None):
            verify_btn = Button("验证", id=f"verify-{btn_id}", variant="primary", classes="verify-btn",
                                compact=True, tooltip="连接实时 AP 并验证凭据")
            setattr(verify_btn, "target_type", target_type)
            return Horizontal(
                Label(f"[bold dim]{label}：[/bold dim] [black bold on lightgreen] {escape(val)} [/]", classes="key-display"),
                Button("复制", id=btn_id, classes="copy-btn", compact=True),
                verify_btn,
                classes="key-row"
            )

        if self._title in ("WPS PSKs", "WPA PSKs"):
            kg.mount(_row("PSK", cap.value or "", "copy-psk", target_type=CaptureType.WPA_PSK))
        elif self._title == "WPS PINs":
            kg.mount(_row("WPS PIN", cap.pin or EMPTY_PIN_LABEL, "copy-pin", target_type=CaptureType.WPS_PIN))
        elif self._title == "WEP KEYs":
            kg.mount(_row("WEP 十六进制密钥", cap.value or "", "copy-hex", target_type=CaptureType.WEP))
            ascii_val = _hex_to_ascii(cap.value)
            if ascii_val:
                kg.mount(_row("ASCII 密钥", ascii_val, "copy-ascii", target_type=CaptureType.WEP))
        elif self._title == "HASHCAT":
            text = self.app.vault.capture_payload(cap)
            hs = sum(1 for ln in text.splitlines() if ln.startswith("WPA*02*"))
            pmkid = sum(1 for ln in text.splitlines() if ln.startswith("WPA*01*"))
            parts = []
            if hs: parts.append(f"{hs} 个握手")
            if pmkid: parts.append(f"{pmkid} 个 PMKID")
            summary = "[italic]" + ("，".join(parts) or "hashcat 22000 文件") + "[/italic]"
            if self._cracked_key:
                summary += (f"   [black bold on lightgreen] 已破解 [/] 密钥："
                            f"[black bold on cyan] {escape(self._cracked_key)} [/]")
            kg.mount(Label(summary, classes="key-display"))
        elif self._title == "HANDSHAKE":
            kg.mount(Label("[italic]原始 .pcap 抓包[/italic]", classes="key-display"))

    @on(Select.Changed)
    def _file_changed(self, event: Select.Changed) -> None:
        self.cancel_verification()
        cap = self._by_path.get(event.value)
        if cap:
            self._update_display(cap)

    @on(Button.Pressed, ".copy-btn")
    def _copy(self, event: Button.Pressed) -> None:
        event.stop()
        cap = self._by_path.get(self.query_one(Select).value)
        if not cap: return
        
        btn_id = event.button.id
        text = ""
        if btn_id == "copy-psk": text = cap.value or ""
        elif btn_id == "copy-pin": text = cap.pin or ""
        elif btn_id == "copy-hex": text = cap.value or ""
        elif btn_id == "copy-ascii": text = _hex_to_ascii(cap.value)
        
        if not text:
            self.notify("此条目没有可复制的内容", severity="warning")
            return
        self.app.copy_to_clipboard(text)
        self.notify("已复制到剪贴板")

    @on(Button.Pressed, ".verify-btn")
    def _verify(self, event: Button.Pressed) -> None:
        event.stop()
        cap = self._by_path.get(self.query_one(Select).value)
        if not cap:
            return
        btn = event.button
        self.cancel_verification()
        target_type = getattr(btn, "target_type", None)
        self._verify_task = asyncio.create_task(self._run_verify(cap, btn, target_type))

    async def _run_verify(self, cap: PersistedCapture, btn: Button, target_type: Optional[CaptureType]) -> None:
        from wifit3.campaigns.live_check import LiveKeyVerifier, VerifyStatus

        btn.disabled = True
        btn.label = "验证中…"
        verifier = LiveKeyVerifier()
        try:
            res = await verifier.verify_credential(cap, self.app.array, target_type=target_type)
            if res.status == VerifyStatus.SUCCESS:
                self.notify(res.body, title=res.title, severity="information")
            elif res.status == VerifyStatus.INCORRECT:
                self.notify(res.body, title=res.title, severity="warning")
            else:
                self.notify(res.body, title=res.title, severity="error")
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception("Error during live verification")
            self.notify(f"验证错误：{exc}", title="验证", severity="error")
        finally:
            btn.label = "验证"
            btn.disabled = False

    @on(Button.Pressed, ".delete")
    def _delete(self, event: Button.Pressed) -> None:
        event.stop()
        cap = self._by_path.get(self.query_one(Select).value)
        if not cap:
            return

        def after(confirmed: bool | None) -> None:
            if not confirmed:
                return
            try:
                logger.info(f"Deleting {cap}")
                self.app.vault.delete_capture(cap)
            except OSError as exc:
                logger.error(f"Could not remove {Path(cap.path).name}: {exc}")
                self.notify(f"无法删除 {Path(cap.path).name}：{exc}", severity="error")
                return
            self.notify(f"已删除 {Path(cap.path).name}")
            self.post_message(VaultItemView.CapturesChanged())

        self.app.push_screen(ConfirmModal(f"删除 [bold]{escape(Path(cap.path).name)}[/]？"), after)
        
    @on(Button.Pressed, ".tool-btn")
    def _launch_tool(self, event: Button.Pressed) -> None:
        event.stop()
        selected_file = self.query_one(Select).value
        cap = self._by_path.get(selected_file)
        if not cap:
            logger.warning(f"Unable to launch tool for {selected_file}: Not found in index")
            return
        
        tool_name = next((c.replace("launch-tool-", "") for c in event.button.classes if c.startswith("launch-tool-")), None)
        if not tool_name:
            return
        
        modal_cls = UI_TOOLS.get(tool_name)
        if not modal_cls:
            logger.error(f"Unable to launch tool: No entry in UI_TOOLS for {tool_name}")
            self.notify(f"未配置该工具的界面：{tool_name}", severity="error")
            return
            
        def _on_config(config: dict | None) -> None:
            if not config:
                return
            job_id = self.app.vault.manager.submit_job(tool_name, cap, config)
            self.notify(f"任务已入队：{job_id}")
            
        self.app.push_screen(modal_cls(), _on_config)

    @on(Button.Pressed, ".open-dir")
    def _open_dir(self, event: Button.Pressed) -> None:
        event.stop()
        selected_file = self.query_one(Select).value
        cap = self._by_path.get(selected_file)
        if not cap:
            logger.warning(f"Unable to open directory, {selected_file} not found in index")
            return
        try:
            path = os.path.normpath(Path(cap.path).resolve())
            if os.name == 'nt':
                subprocess.Popen(['explorer.exe', '/select,', path])
            else:
                subprocess.Popen(['xdg-open', str(Path(path).parent)])
        except Exception as exc:
            logger.error(f"Failed to open directory for {cap}", exc)
            self.notify(f"无法打开目录：{exc}", severity="error")


class VaultItemView(Vertical):
    class CapturesChanged(Message):
        """A capture was deleted; the parent should refresh."""

    DEFAULT_CSS = """
    VaultItemView {
        width: 1fr;
        height: 1fr;
        align-horizontal: center;
        background: $background;
        border: heavy $primary;
        border-title-align: center;
        border-title-color: $primary;
        border-title-style: bold;
        padding: 0 1;
        overflow-y: auto;
        scrollbar-size-vertical: 1;
    }
    VaultItemView #vault-item-empty { color: $text-muted; }
    """

    _state: reactive[tuple] = reactive(("", None, ()), recompose=True)

    def cancel_verification(self) -> None:
        """Cancel any running verification tasks on active capture panels."""
        for panel in self.query(_CapturePanel):
            panel.cancel_verification()

    def load(self, bssid: str, ssid: Optional[str], captures: List[PersistedCapture]) -> None:
        self.cancel_verification()
        self._state = (bssid, ssid, tuple(captures))

    def compose(self) -> ComposeResult:
        bssid, ssid, captures = self._state
        if not bssid:
            self.border_title = "保险库详情"
            yield Label("选择一个 AP 查看其抓包", id="vault-item-empty")
            return
            
        name = ssid or "‹隐藏›"
        self.border_title = f"[$background bold on $primary] {escape(name)} ({escape(bssid)}) [/]"
        
        groups = {
            "HANDSHAKE": [c for c in captures if c.path.endswith(".pcap")],
            "HASHCAT": [c for c in captures if c.path.endswith(".hc22000")],
            "WPA PSKs": [c for c in captures if c.type == CaptureType.WPA_PSK and c.value],
            "WPS PSKs": [c for c in captures if c.type in (CaptureType.WPS_PIN, CaptureType.WPS_PBC) and c.value],
            "WPS PINs": [c for c in captures if c.type == CaptureType.WPS_PIN and c.pin is not None],
            "WEP KEYs": [c for c in captures if c.type == CaptureType.WEP],
        }
        cracked_key = next((c.value for c in captures if c.type == CaptureType.WPA_PSK and c.value), None)
        for title, group in groups.items():
            if group:
                yield _CapturePanel(title, group, cracked_key=cracked_key if title == "HASHCAT" else None)
