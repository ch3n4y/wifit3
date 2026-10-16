"""macOS device setup: no privileged step. macOS ships no driver for wifit3's RTL/MT/RT/AR chips,
so libusb claims them directly. install returns the device for one connect retry; uninstall
reports there is nothing to remove.
"""
from __future__ import annotations

from wifit3.models import DeviceID
from wifit3.setup.base import Prompter, Setup, SetupResult

_NOOP_MSG = "macOS 无需驱动设置。正在重试连接…"
_UNINSTALL_MSG = "macOS 上未安装任何内容：没有需要移除的驱动绑定或访问规则。"


class SetupMacOS(Setup):
    """No-op macOS setup: install returns the device for one connect retry, uninstall reports
    there is nothing to remove."""

    async def install(self, device_id: DeviceID, ui: Prompter) -> DeviceID | None:
        ui.status(_NOOP_MSG)
        return device_id

    async def uninstall(self, device_id: DeviceID, ui: Prompter) -> SetupResult:
        return SetupResult(ok=True, message=_UNINSTALL_MSG)
