"""Enumerate every content source in load order.

CK3 resolves a file by walking the enabled mod list top-to-bottom and letting the
LAST source that provides a given relative path win. Vanilla is always first and
therefore always loses to any mod. Everything in this workspace that reasons
about overrides uses this ordering.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .paths import Config
from .pdxscript import parse_descriptor, read_text

VANILLA = "vanilla"
WORKSHOP = "workshop"
LOCAL = "local"


@dataclass(frozen=True)
class Source:
    kind: str
    name: str
    root: Path
    order: int
    mod_id: str | None = None
    descriptor: Path | None = None
    version: str | None = None
    supported_version: str | None = None

    @property
    def label(self) -> str:
        return f"{self.name} [{self.mod_id}]" if self.mod_id else self.name


def _descriptor_of(mod_root: Path, mod_file: Path | None) -> Path | None:
    inner = mod_root / "descriptor.mod"
    if inner.is_file():
        return inner
    return mod_file if mod_file and mod_file.is_file() else None


def _descriptor_meta(
    descriptor: Path | None,
    mod_file: Path,
    stub: dict,
) -> dict:
    """Version metadata, preferring the mod's own `descriptor.mod` over the stub.

    The launcher writes a pointer file per enabled mod into `<user>/mod/`, and
    that stub carries a *copy* of the mod's descriptor fields. Steam updates the
    workshop folder without rewriting the stub, so after an update the stub can
    claim `supported_version="1.16.*.*"` while the mod itself already declares
    1.19. The game loads the real files, so the inner descriptor is the truth.
    """
    if descriptor is None or descriptor == mod_file:
        return stub
    try:
        inner = parse_descriptor(read_text(descriptor))
    except OSError:
        return stub
    merged = dict(stub)
    for key in ("version", "supported_version"):
        value = inner.get(key)
        if isinstance(value, str) and value:
            merged[key] = value
    return merged


def read_mod_file(cfg: Config, mod_file: Path, order: int) -> Source | None:
    """Turn a `<user>/mod/*.mod` pointer file into a Source."""
    if not mod_file.is_file():
        return None
    data = parse_descriptor(read_text(mod_file))
    raw_path = data.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        return None
    root = Path(raw_path)
    if not root.is_absolute():
        root = cfg.user_dir / raw_path
    remote = data.get("remote_file_id")
    kind = WORKSHOP if remote else LOCAL
    descriptor = _descriptor_of(root, mod_file)
    meta = _descriptor_meta(descriptor, mod_file, data)
    return Source(
        kind=kind,
        name=str(data.get("name") or mod_file.stem),
        root=root,
        order=order,
        mod_id=str(remote) if remote else None,
        descriptor=descriptor,
        version=str(meta.get("version") or ""),
        supported_version=str(meta.get("supported_version") or ""),
    )


def enabled_mods(cfg: Config) -> list[str]:
    if not cfg.dlc_load.is_file():
        return []
    data = json.loads(cfg.dlc_load.read_text(encoding="utf-8"))
    return list(data.get("enabled_mods", []))


def playset_sources(cfg: Config, include_vanilla: bool = True) -> list[Source]:
    """Vanilla plus every enabled mod, in load order (last wins)."""
    sources: list[Source] = []
    if include_vanilla:
        sources.append(Source(kind=VANILLA, name="Crusader Kings III", root=cfg.game_root, order=0))
    for i, rel in enumerate(enabled_mods(cfg), start=1):
        source = read_mod_file(cfg, cfg.user_dir / rel, i)
        if source is not None:
            sources.append(source)
    return sources


def workspace_mods(cfg: Config) -> list[Source]:
    """Mod sources authored in this workspace (D:/ck3/mods/*)."""
    found: list[Source] = []
    if not cfg.mods_src.is_dir():
        return found
    for entry in sorted(cfg.mods_src.iterdir()):
        descriptor = entry / "descriptor.mod"
        if not descriptor.is_file():
            continue
        data = parse_descriptor(read_text(descriptor))
        found.append(
            Source(
                kind=LOCAL,
                name=str(data.get("name") or entry.name),
                root=entry,
                order=10_000,
                descriptor=descriptor,
                version=str(data.get("version") or ""),
                supported_version=str(data.get("supported_version") or ""),
            )
        )
    return found


SCRIPT_EXTS = {".txt", ".yml", ".gui", ".asset", ".info", ".shader", ".gfx", ".mod"}
SCAN_DIRS = (
    "common",
    "events",
    "history",
    "localization",
    "gui",
    "map_data",
    "data_binding",
    "music",
    "sound",
    "notifications",
    "gfx",
    "fonts",
    "dlc",
)


def iter_files(root: Path, exts: set[str] | None = None):
    """Yield (relpath_posix, absolute_path) for content files under `root`."""
    exts = exts if exts is not None else SCRIPT_EXTS
    for top in SCAN_DIRS:
        base = root / top
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if exts and path.suffix.lower() not in exts:
                continue
            yield path.relative_to(root).as_posix(), path
