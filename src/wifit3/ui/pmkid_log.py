"""Rich-markup rendering for the active PMKID harvest, as a 4-way-handshake-style tree.

Built from per-line fragments (a ``PMKID · Harvesting from <essid>`` header, the
auth/assoc/M1 action branches, and the terminal verdict) so the SAME builders
serve two emit modes: composed into one list for an atomic dump today, and called
one-at-a-time on live progress events once the harvest becomes a campaign. Pure +
UI-free (testable without a terminal); the screen owns side effects (save, log).

Field ticks (``PMKID✓/✗``) reuse the 4-way handshake's glyphs; the heavy ``╳``
is reserved for the terminal give-up connector (``treelog.leaf_fail``).
"""
from __future__ import annotations

from typing import Optional

from wifit3.campaigns import treelog
from wifit3.campaigns.pmkid import PmkidFail

_M1_DIR = "AP→客户端"
_REQ_DIR = "客户端→AP"
_EXTRACTED = "[black bold on green] ✓ 已提取 PMKID [/black bold on green]"

# reason -> (styled headline markup, dim parenthetical why).
_FAIL_LEAF = {
    PmkidFail.NO_KDE:       ("[black bold on orange1] M1 中无 PMKID [/black bold on orange1]",
                             "AP 不在 M1 中发送 PMKID"),
    PmkidFail.NO_RESPONSE:  ("[bold bright_red]未收到 M1[/bold bright_red]", "AP 未响应"),
    PmkidFail.PMF_REQUIRED: ("[bold orange1]需要 PMF[/bold orange1]",
                             "AP 只关联受保护的客户端"),
    PmkidFail.NO_PSK_AKM:   ("[bold orange1]无 PSK AKM[/bold orange1]",
                             "无可收集内容，例如仅 SAE"),
}

# Reasons reached only AFTER we transmit Auth+Assoc, so their tree echoes those
# branches. PMF / NO_PSK bail before any TX → header + leaf only.
_AFTER_TX = (PmkidFail.NO_RESPONSE, PmkidFail.NO_KDE)


def header(essid: str) -> str:
    return f"[bold]正在收集 PMKID[/bold] 来自 [bold cyan]{essid}[/bold cyan]"


def auth_req() -> str:
    return treelog.branch(f"认证请求 ({_REQ_DIR})")


def assoc_req() -> str:
    return treelog.branch(f"关联请求 ({_REQ_DIR})")


def m1(has_pmkid: bool) -> str:
    tick = "[green]✓[/green]" if has_pmkid else "[red]✗[/red]"
    return treelog.branch(f"M1 消息 ({_M1_DIR}) PMKID{tick}")


def _fail_leaf(reason: Optional[PmkidFail]) -> str:
    head, why = _FAIL_LEAF.get(reason, ("[bold orange1]收集失败[/bold orange1]", ""))
    tail = f" [dim]({why})[/dim]" if why else ""
    return treelog.leaf(f"{head}{tail}")


def verdict_success(save_hint: Optional[str]) -> list[str]:
    """The terminal success line(s) only: the ``✓ PMKID Extracted`` chip closed by
    the ``saved/exists: …`` leaf (or the chip alone as the closing leaf when
    ``save_hint`` is None). Emitted on its own once progress streams live."""
    if save_hint:
        return [treelog.branch(_EXTRACTED), treelog.leaf(save_hint)]
    return [treelog.leaf(_EXTRACTED)]


def verdict_failure(reason: Optional[PmkidFail]) -> list[str]:
    """The terminal give-up line only (bold-orange ``└─╳`` leaf). Emitted on its own
    once the auth/assoc/M1 branches stream live."""
    return [_fail_leaf(reason)]


def render_success(essid: str, save_hint: Optional[str]) -> list[str]:
    """Header → auth → assoc → ``M1 … PMKID✓`` → the success verdict. Atomic-dump
    form; the streaming path emits ``header`` + branches + ``verdict_success``
    separately."""
    return [header(essid), auth_req(), assoc_req(), m1(True)] + verdict_success(save_hint)


def render_failure(essid: str, reason: Optional[PmkidFail]) -> list[str]:
    """Header, the auth/assoc branches (only for reasons reached after TX), an
    ``M1 … PMKID✗`` branch (NO_KDE only, its M1 arrived KDE-less), then the
    failure verdict. Atomic-dump form (see ``verdict_failure`` for the streaming
    terminal line)."""
    lines = [header(essid)]
    if reason in _AFTER_TX:
        lines += [auth_req(), assoc_req()]
    if reason is PmkidFail.NO_KDE:
        lines.append(m1(False))
    return lines + verdict_failure(reason)
