#!/usr/bin/env python3
"""Which English UI strings still need translating?

Run this after every upstream sync (the workflow is in `docs/i18n/SYNC.zh-CN.md`). It scans
the surface this fork localizes -- the Textual UI, the campaign text that renders into the
Focus log pane, the setup prompts, and the two user-facing error modules -- and compares the
English string literals it finds against a checked-in baseline of strings we knowingly keep
in English (logger lines, protocol names, command lines, ...).

    NEW    In the tree but not in the baseline: a new upstream string. Review it, then either
           translate it (the normal case) or add it to the baseline (if it is not user text).
    STALE  In the baseline but no longer in the tree: upstream removed or reworded that line.
           Drop it from the baseline; if it was reworded into new user-facing text, the new
           wording shows up under NEW.

Usage:
    python tools/i18n_audit.py --init     # (re)write the baseline from the current tree
    python tools/i18n_audit.py            # report NEW / STALE
    python tools/i18n_audit.py --strict   # same, but exit 1 when NEW is non-empty
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs" / "i18n" / "english-baseline.json"

# The localized surface: everything the zh-CN pass rewrites, plus the error text the TUI
# renders in its modals.
TARGETS = (
    "src/wifit3/ui",
    "src/wifit3/campaigns",
    "src/wifit3/setup",
    "src/wifit3/errors.py",
    "src/wifit3/device/manager.py",
)

CJK = re.compile(r"[\u3400-\u9fff\u3000-\u303f\uff00-\uffef]")
TWO_WORDS = re.compile(r"[A-Za-z]{2,}[ \t][A-Za-z]{2,}")
TITLE_WORD = re.compile(r"[A-Z][a-z]{2,}")
# Text that is never prose: Rich/CSS only, format specifiers, paths, ids and keys.
NOISE = re.compile(r"[{};]|%[sdfrx]|\x00|^[-/.\\]|^[a-z0-9_.:-]+$")


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for target in TARGETS:
        path = ROOT / target
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        elif path.is_file():
            files.append(path)
    return files


STYLE_WORDS = frozenset({"on", "bold", "dim", "italic", "underline", "reverse", "strike", "blink",
                         "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"})


def is_style(text: str) -> bool:
    """True for a Rich style value ("black bold on cyan"), which is not prose."""
    words = text.split()
    return bool(words) and all(w in STYLE_WORDS or w.startswith(("bright_", "dark_")) for w in words)
def docstring_nodes(tree: ast.AST) -> set[int]:
    """Every string that documents code: module/class/function/attribute docstrings."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                found.add(id(body[0].value))
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            found.add(id(node.value))
    return found


def is_candidate(text: str) -> bool:
    """True when `text` looks like English prose a user could read."""
    if len(text.strip()) < 2 or CJK.search(text):
        return False
    if not any(char.isalpha() for char in text):
        return False
    if NOISE.search(text):
        return False
    if is_style(text):
        return False
    return bool(TWO_WORDS.search(text) or TITLE_WORD.match(text))


def scan() -> dict[str, list[str]]:
    """{literal: ["path:line", ...]} for every candidate in the tree."""
    hits: dict[str, list[str]] = {}
    for path in iter_python_files():
        rel = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        skip = docstring_nodes(tree)
        for node in ast.walk(tree):
            parts: list[tuple[int, str]] = []
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
                parts.append((node.lineno, node.value))
            elif isinstance(node, ast.JoinedStr):
                parts.extend((part.lineno, part.value) for part in node.values
                             if isinstance(part, ast.Constant) and isinstance(part.value, str))
            for lineno, text in parts:
                if is_candidate(text):
                    hits.setdefault(text, []).append(f"{rel}:{lineno}")
    return hits


def load_baseline() -> set[str]:
    if not BASELINE.is_file():
        return set()
    return set(json.loads(BASELINE.read_text(encoding="utf-8")))


def write_baseline(entries: set[str]) -> None:
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps(sorted(entries), indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--init", action="store_true",
                        help="write the baseline from the current tree (accept everything now present)")
    parser.add_argument("--strict", action="store_true", help="exit 1 when NEW is non-empty")
    args = parser.parse_args()

    found = scan()
    if args.init:
        write_baseline(set(found))
        print(f"baseline written: {BASELINE.relative_to(ROOT).as_posix()} "
              f"({len(found)} English strings accepted)")
        return 0

    baseline = load_baseline()
    new = sorted(text for text in found if text not in baseline)
    stale = sorted(text for text in baseline if text not in found)

    print(f"NEW ({len(new)})")
    for text in new:
        print(f"  {found[text][0]}: {text}")
    print(f"\nSTALE ({len(stale)})")
    for text in stale:
        print(f"  {text}")
    print(f"\nbaseline: {BASELINE.relative_to(ROOT).as_posix()} "
          f"({len(baseline)} accepted, {len(found)} seen in the tree)")

    if args.strict and new:
        print("\n--strict: translate the NEW strings, or accept them with --init")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
