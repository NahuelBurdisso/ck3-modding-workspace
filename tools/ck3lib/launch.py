"""Launch the game and collect diagnostics.

Notes that cost real time to learn:
  - Steam must already be running; ck3.exe will not start it.
  - In -debug_mode CK3 writes errors to stdout as well as to error.log. Capture
    the WHOLE stream to a file - piping it through `tail` throws away everything
    but trailing checksum spam.
  - `logs/` stays empty during a run and after a clean exit. Empty logs after a
    full session means no errors, not "not written yet".
  - The process ignores WM_CLOSE, so it cannot be closed programmatically; quit
    from the in-game menu.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .paths import Config

ERROR_MARKERS = ("[E]", "Error:", "error:", "[ERROR]", "failed", "Failed")


def launch(cfg: Config, debug: bool = True, extra_args: list[str] | None = None) -> Path:
    if not cfg.exe.is_file():
        raise SystemExit(f"ck3.exe not found at {cfg.exe}")
    cfg.run_logs.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    capture = cfg.run_logs / f"run-{stamp}.log"
    args = [str(cfg.exe)]
    if debug:
        args.append("-debug_mode")
    args.extend(extra_args or [])
    handle = capture.open("wb")
    subprocess.Popen(
        args,
        cwd=str(cfg.exe.parent),
        stdout=handle,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
    )
    return capture


def clear_game_logs(cfg: Config) -> int:
    """Empty <user dir>/logs so the next run's errors are unambiguous."""
    removed = 0
    if not cfg.game_logs.is_dir():
        return 0
    for path in cfg.game_logs.iterdir():
        if path.is_file():
            path.unlink()
            removed += 1
    return removed


def collect_errors(cfg: Config, tail: int = 80) -> dict[str, list[str]]:
    """Error lines from the game's own logs plus our newest stdout capture."""
    out: dict[str, list[str]] = {}
    if cfg.game_logs.is_dir():
        for path in sorted(cfg.game_logs.glob("*.log")):
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            if lines:
                out[path.name] = lines[-tail:]
    captures = sorted(cfg.run_logs.glob("run-*.log"))
    if captures:
        newest = captures[-1]
        lines = newest.read_text(encoding="utf-8", errors="replace").splitlines()
        flagged = [line for line in lines if any(marker in line for marker in ERROR_MARKERS)]
        out[newest.name] = flagged[-tail:] if flagged else []
    return out
