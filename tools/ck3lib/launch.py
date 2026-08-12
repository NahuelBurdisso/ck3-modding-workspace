"""Launch the game and collect diagnostics.

Notes that cost real time to learn:
  - Steam must already be running; ck3.exe will not start it.
  - stdout is NOT where results live. Even in -debug_mode the captured stream is
    almost entirely [Checksum Builder] spam, and that spam is not a file
    manifest - mods that are definitely loaded never appear in it. Everything
    useful goes to <user dir>/logs/: debug.log (every `debug_log = "..."`, plus
    the authoritative `<Name>|mod/<file>.mod|Enabled` manifest), error.log
    (names the file behind every complaint) and game.log.
  - `logs/` is written during the run, but CK3 only creates error.log when
    something actually failed. Empty logs/ after a full session means a clean
    run, not "not written yet".
  - debug.log routinely reaches tens of MB. Tailing it is useless; grep it for
    your own markers instead - see `probe()`.
  - The process ignores WM_CLOSE, so it cannot be closed programmatically; quit
    from the in-game menu.
"""

from __future__ import annotations

import re
import subprocess
import time
from collections import Counter
from pathlib import Path

from .paths import Config

ERROR_MARKERS = ("[E]", "Error:", "error:", "[ERROR]", "failed", "Failed")

# Log lines are prefixed with one or more bracketed fields, e.g.
# "[14:52:03][jomini_onaction.cpp:161]: There is more than one 'effect'..."
_PREFIX = re.compile(r"^(?:\[[^\]]*\])+\s*:?\s*")


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


def probe(cfg: Config, pattern: str, ignore_case: bool = False) -> dict[str, Counter]:
    """Count matching lines in <user dir>/logs, grouped by message.

    This is how a probe run is actually read. debug.log reaches tens of MB in a
    single session, so paging or tailing it is worthless; the question is always
    "how many times did marker X fire", and a marker that fired 41 times and one
    that fired once mean very different things. Timestamps and source-file
    prefixes are stripped so repeats collapse into one row.

    Returns {log file name: Counter(message -> hits)}.
    """
    rx = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
    out: dict[str, Counter] = {}
    if not cfg.game_logs.is_dir():
        return out
    for path in sorted(cfg.game_logs.glob("*.log")):
        counts: Counter = Counter()
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if rx.search(line):
                    counts[_PREFIX.sub("", line.strip())] += 1
        if counts:
            out[path.name] = counts
    return out


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
