"""Path resolution for the CK3 modding workspace.

Every other module goes through Config so there is exactly one place that knows
where the game, the user directory and the workshop live.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
CONFIG_FILE = WORKSPACE / "ck3.config.json"


@dataclass(frozen=True)
class Config:
    game_dir: Path
    user_dir: Path
    workshop_dir: Path
    workspace_dir: Path
    app_id: str
    base_mod_id: str
    supported_version: str
    loc_languages: tuple[str, ...] = ("english", "spanish")

    # --- derived ---------------------------------------------------------
    @property
    def game_root(self) -> Path:
        """The `game/` folder: the one that mirrors a mod's own structure."""
        return self.game_dir / "game"

    @property
    def exe(self) -> Path:
        return self.game_dir / "binaries" / "ck3.exe"

    @property
    def mod_dir(self) -> Path:
        return self.user_dir / "mod"

    @property
    def dlc_load(self) -> Path:
        return self.user_dir / "dlc_load.json"

    @property
    def game_logs(self) -> Path:
        return self.user_dir / "logs"

    @property
    def mods_src(self) -> Path:
        """Where our own mod sources live (git-tracked)."""
        return self.workspace_dir / "mods"

    @property
    def index_db(self) -> Path:
        return self.workspace_dir / "index" / "ck3.sqlite3"

    @property
    def run_logs(self) -> Path:
        return self.workspace_dir / "logs"

    def check(self) -> list[str]:
        problems = []
        if not self.game_root.is_dir():
            problems.append(f"game_dir invalid: {self.game_root} not found")
        if not self.user_dir.is_dir():
            problems.append(f"user_dir invalid: {self.user_dir} not found")
        if not self.workshop_dir.is_dir():
            problems.append(f"workshop_dir invalid: {self.workshop_dir} not found")
        return problems


def load_config() -> Config:
    raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    for key in ("game_dir", "user_dir", "workshop_dir", "workspace_dir"):
        raw[key] = Path(os.path.expandvars(raw[key]))
    if "loc_languages" in raw:
        raw["loc_languages"] = tuple(raw["loc_languages"])
    return Config(**raw)


def version_matches(supported: str, game: str) -> bool:
    """Compare a mod's `supported_version` against the installed game version.

    Mods routinely declare wildcards such as `1.*` or `*.*.*`, which match any
    value in that position. Only the segments both strings actually have are
    compared, so `1.19` and `1.19.0.6` agree.
    """
    if not supported or not game:
        return True
    left = supported.split(".")
    right = game.split(".")
    for a, b in zip(left, right):
        if a == "*" or b == "*":
            continue
        if a != b:
            return False
    return True


def to_pdx_path(path: Path) -> str:
    """CK3 rejects mixed separators in `path=`; always emit forward slashes."""
    return str(path).replace("\\", "/")
