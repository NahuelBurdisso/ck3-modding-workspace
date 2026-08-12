"""Create a new mod skeleton and wire it into the game.

Mods are authored in D:/ck3/mods/<slug> and exposed to CK3 through a pointer
file at <user dir>/mod/<slug>.mod whose `path=` is absolute. No copying and no
symlinks: edit in place, restart the game, done.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from .paths import Config, to_pdx_path
from .pdxscript import BOM, parse_descriptor, read_text

DEFAULT_DIRS = (
    "common/scripted_effects",
    "common/scripted_triggers",
    "common/on_action",
    "events",
    "localization/english",
    "gui",
)

VALID_SLUG = re.compile(r"^[a-z0-9_]+$")

GITIGNORE = """# CK3 build noise
*.pdx_bak
thumbnail_backup.png
"""


def write_lf(path: Path, text: str) -> None:
    """Write UTF-8 with LF endings; Windows would otherwise inject CRLF."""
    path.write_text(text, encoding="utf-8", newline="\n")


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return re.sub(r"_+", "_", slug)


def descriptor_text(
    name: str,
    version: str,
    supported_version: str,
    tags: list[str],
    dependencies: list[str],
    path: str | None = None,
) -> str:
    lines = [f'version="{version}"']
    lines.append("tags={")
    lines.extend(f'\t"{tag}"' for tag in tags)
    lines.append("}")
    if dependencies:
        lines.append("dependencies={")
        lines.extend(f'\t"{dep}"' for dep in dependencies)
        lines.append("}")
    lines.append(f'name="{name}"')
    lines.append(f'supported_version="{supported_version}"')
    if path:
        lines.append(f'path="{path}"')
    return "\n".join(lines) + "\n"


def base_mod_name(cfg: Config) -> str | None:
    """Resolve the display name of the configured base mod (for dependencies=)."""
    if not cfg.base_mod_id:
        return None
    descriptor = cfg.workshop_dir / cfg.base_mod_id / "descriptor.mod"
    if not descriptor.is_file():
        return None
    value = parse_descriptor(read_text(descriptor)).get("name")
    return str(value) if value else None


def create_mod(
    cfg: Config,
    name: str,
    *,
    slug: str | None = None,
    tags: list[str] | None = None,
    depend_on_base: bool = False,
    git: bool = True,
) -> Path:
    slug = slug or slugify(name)
    if not VALID_SLUG.match(slug):
        raise SystemExit(f"invalid slug `{slug}`: use lowercase letters, digits and underscores")
    mod_root = cfg.mods_src / slug
    if mod_root.exists():
        raise SystemExit(f"already exists: {mod_root}")

    tags = tags or ["Gameplay"]
    dependencies = []
    if depend_on_base:
        base = base_mod_name(cfg)
        if not base:
            raise SystemExit(f"cannot resolve base mod name for id {cfg.base_mod_id}; is it installed?")
        dependencies.append(base)

    for folder in DEFAULT_DIRS:
        (mod_root / folder).mkdir(parents=True, exist_ok=True)

    write_lf(
        mod_root / "descriptor.mod",
        descriptor_text(name, "1.0.0", cfg.supported_version, tags, dependencies),
    )
    write_lf(mod_root / ".gitignore", GITIGNORE)

    # CWTools only resolves its rules when the mod folder is the workspace root,
    # so each mod carries its own editor config.
    vscode = mod_root / ".vscode"
    vscode.mkdir(exist_ok=True)
    write_lf(
        vscode / "settings.json",
        json.dumps(
            {
                "cwtools.cache.ck3": to_pdx_path(cfg.game_dir),
                "cwtools.rules_version": "latest",
                "cwtools.localisation.languages": ["English"],
                "cwtools.errors.vanilla": False,
                "files.eol": "\n",
                "[yaml]": {"files.encoding": "utf8bom"},
            },
            indent=2,
        )
        + "\n",
    )

    write_lf(
        mod_root / "localization" / "english" / f"{slug}_l_english.yml",
        f'{BOM}l_english:\n {slug.upper()}_PLACEHOLDER:0 "{name}"\n',
    )
    write_lf(
        mod_root / "common" / "scripted_triggers" / f"{slug}_scripted_triggers.txt",
        f"# {name} - scripted triggers\n"
        f"# Prefix every key with `{slug}_` so it can never collide with vanilla or another mod.\n",
    )
    write_lf(
        mod_root / "common" / "scripted_effects" / f"{slug}_scripted_effects.txt",
        f"# {name} - scripted effects\n",
    )
    write_lf(
        mod_root / "events" / f"{slug}_events.txt",
        f"namespace = {slug}\n\n"
        f"# {slug}.0001 = {{\n"
        f"#     type = character_event\n"
        f"#     title = {slug}.0001.t\n"
        f"#     desc = {slug}.0001.desc\n"
        f"#     theme = default\n"
        f"#     option = {{ name = {slug}.0001.a }}\n"
        f"# }}\n",
    )
    write_lf(
        mod_root / "README.md",
        f"# {name}\n\n"
        f"Source for the CK3 mod `{slug}`.\n\n"
        f"- Deploy:   `python tools/ck3.py deploy {slug}`\n"
        f"- Validate: `python tools/ck3.py validate {slug}`\n"
        f"- Enable:   `python tools/ck3.py playset add {slug}`\n",
    )

    if git:
        subprocess.run(["git", "init", "-q"], cwd=mod_root, check=False)
    return mod_root


def deploy(cfg: Config, mod_root: Path) -> Path:
    """Write/refresh <user dir>/mod/<slug>.mod pointing at the source folder."""
    descriptor = mod_root / "descriptor.mod"
    if not descriptor.is_file():
        raise SystemExit(f"no descriptor.mod in {mod_root}")
    data = parse_descriptor(read_text(descriptor))
    tags = data.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    dependencies = data.get("dependencies") or []
    if isinstance(dependencies, str):
        dependencies = [dependencies]

    text = descriptor_text(
        str(data.get("name", mod_root.name)),
        str(data.get("version", "1.0.0")),
        str(data.get("supported_version", cfg.supported_version)),
        list(tags),
        list(dependencies),
        path=to_pdx_path(mod_root),
    )
    cfg.mod_dir.mkdir(parents=True, exist_ok=True)
    target = cfg.mod_dir / f"{mod_root.name}.mod"
    write_lf(target, text)
    return target


def sync_workshop_pointer(cfg: Config, mod_id: str) -> Path:
    """Regenerate <user dir>/mod/ugc_<id>.mod from the workshop descriptor."""
    source = cfg.workshop_dir / mod_id / "descriptor.mod"
    if not source.is_file():
        raise SystemExit(f"workshop item {mod_id} not installed at {source.parent}")
    text = read_text(source)
    data = parse_descriptor(text)
    lines = [line for line in text.splitlines() if not line.strip().startswith("path=")]
    if "remote_file_id" not in data:
        lines.append(f'remote_file_id="{mod_id}"')
    lines.append(f'path="{to_pdx_path(cfg.workshop_dir / mod_id)}"')
    cfg.mod_dir.mkdir(parents=True, exist_ok=True)
    target = cfg.mod_dir / f"ugc_{mod_id}.mod"
    write_lf(target, "\n".join(lines) + "\n")
    return target
