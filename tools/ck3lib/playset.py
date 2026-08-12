"""Read and edit the active playset directly through dlc_load.json.

The Paradox launcher is optional: the game itself only reads dlc_load.json, and
the order of `enabled_mods` IS the load order (last entry wins). Opening the
launcher regenerates this file from its own database and discards edits made
here, so launch ck3.exe directly after changing the playset.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from .paths import Config, version_matches
from .sources import read_mod_file


def read(cfg: Config) -> dict:
    if not cfg.dlc_load.is_file():
        return {"disabled_dlcs": [], "enabled_mods": []}
    return json.loads(cfg.dlc_load.read_text(encoding="utf-8"))


def backup(cfg: Config) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = cfg.workspace_dir / "index" / "playset-backups" / f"dlc_load-{stamp}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cfg.dlc_load, target)
    return target


def write(cfg: Config, data: dict) -> Path:
    backup(cfg)
    cfg.dlc_load.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return cfg.dlc_load


def entries(cfg: Config) -> list[tuple[int, str, str]]:
    """(position, `mod/xxx.mod`, resolved display name) in load order."""
    out = []
    for i, rel in enumerate(read(cfg).get("enabled_mods", [])):
        source = read_mod_file(cfg, cfg.user_dir / rel, i)
        out.append((i, rel, source.name if source else "<missing .mod file>"))
    return out


def _entry_for(name: str) -> str:
    if name.startswith("mod/"):
        return name if name.endswith(".mod") else f"{name}.mod"
    if name.isdigit():
        return f"mod/ugc_{name}.mod"
    return f"mod/{name}.mod"


def add(cfg: Config, name: str, position: int | None = None) -> str:
    data = read(cfg)
    entry = _entry_for(name)
    mods = data.setdefault("enabled_mods", [])
    if entry in mods:
        mods.remove(entry)
    if position is None:
        mods.append(entry)
    else:
        mods.insert(max(0, min(position, len(mods))), entry)
    write(cfg, data)
    return entry


def remove(cfg: Config, name: str) -> str:
    data = read(cfg)
    entry = _entry_for(name)
    mods = data.setdefault("enabled_mods", [])
    if entry not in mods:
        raise SystemExit(f"{entry} is not in the playset")
    mods.remove(entry)
    write(cfg, data)
    return entry


def move(cfg: Config, name: str, position: int) -> str:
    return add(cfg, name, position)


def audit(cfg: Config) -> list[str]:
    """Structural problems in the current playset."""
    problems: list[str] = []
    seen: set[str] = set()
    for pos, rel, name in entries(cfg):
        pointer = cfg.user_dir / rel
        if not pointer.is_file():
            problems.append(f"[{pos}] {rel}: pointer .mod file missing")
            continue
        source = read_mod_file(cfg, pointer, pos)
        if source is None:
            problems.append(f"[{pos}] {rel}: descriptor has no usable path=")
            continue
        if not source.root.is_dir():
            problems.append(f"[{pos}] {name}: content folder missing -> {source.root}")
        if not version_matches(source.supported_version or "", cfg.supported_version):
            problems.append(
                f"[{pos}] {name}: supported_version {source.supported_version} vs game {cfg.supported_version}"
            )
        if rel in seen:
            problems.append(f"[{pos}] {rel}: duplicate entry in enabled_mods")
        seen.add(rel)
    return problems
