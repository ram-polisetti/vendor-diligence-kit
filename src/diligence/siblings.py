"""Locate and import pinned sibling checkouts.

Sibling repos are found via the ``DILIGENCE_SIBLINGS`` environment variable
(``name=path`` pairs, comma- or os.pathsep-separated) or a
``.diligence-siblings.json`` file in the working directory. Adapters import the
sibling packages lazily so a missing sibling fails only the step that needs it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from .pins import PINS, SRC_LAYOUTS

_warnings: list[str] = []


def warnings() -> list[str]:
    return list(_warnings)


def sibling_roots() -> dict[str, Path]:
    roots: dict[str, Path] = {}
    raw = os.environ.get("DILIGENCE_SIBLINGS", "")
    for chunk in raw.replace(",", os.pathsep).split(os.pathsep):
        if "=" in chunk:
            name, path = chunk.split("=", 1)
            roots[name.strip()] = Path(path.strip()).expanduser()
    cfg = Path.cwd() / ".diligence-siblings.json"
    if cfg.exists():
        try:
            for name, path in json.loads(cfg.read_text()).items():
                roots.setdefault(name, Path(str(path)).expanduser())
        except (json.JSONDecodeError, AttributeError):
            _warnings.append(f"could not parse {cfg}; ignoring")
    # Fallback: the standard workspace layout used by the fleet.
    for name in PINS:
        if name not in roots:
            guess = Path.home() / "workspace" / "p18" / name
            if guess.exists():
                roots[name] = guess
    return roots


def _git_sha(root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def import_sibling(name: str):
    """Import ``name``'s package from its checkout; verify the pinned SHA."""
    roots = sibling_roots()
    root = roots.get(name)
    if root is None or not root.exists():
        raise ImportError(
            f"sibling '{name}' not found. Set DILIGENCE_SIBLINGS={name}=/path "
            f"or add it to .diligence-siblings.json"
        )
    layout, _pkg = SRC_LAYOUTS[name]
    src_dir = root / layout
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    pinned = PINS.get(name)
    actual = _git_sha(root)
    if pinned and actual and not actual.startswith(pinned):
        _warnings.append(
            f"sibling '{name}': checkout is {actual}, pinned {pinned} — "
            "results may not reproduce the pinned version"
        )
    elif pinned and actual and actual.startswith(pinned):
        pass  # exact match, silent
    return actual or "unknown"
