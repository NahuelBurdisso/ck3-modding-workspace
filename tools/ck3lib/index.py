"""SQLite index over vanilla + the enabled playset + workspace mods.

Answers the three questions that otherwise cost a full-disk scan every time:
  - which sources ship this file, and which one wins? (`where`)
  - where is this key defined? (`find`)
  - which mods fight over the same file? (`conflicts`)
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from .paths import Config
from .pdxscript import keys_matching, parse_loc, read_text, top_level_defs
from .sources import Source, iter_files, playset_sources, workspace_mods

SCHEMA = """
PRAGMA journal_mode = OFF;
PRAGMA synchronous = OFF;

DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS files;
DROP TABLE IF EXISTS defs;
DROP TABLE IF EXISTS loc;

CREATE TABLE sources (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    mod_id TEXT,
    root TEXT NOT NULL,
    load_order INTEGER NOT NULL,
    version TEXT,
    supported_version TEXT
);
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    relpath TEXT NOT NULL,
    ext TEXT NOT NULL,
    size INTEGER NOT NULL
);
CREATE TABLE defs (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES files(id),
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    line INTEGER NOT NULL
);
CREATE TABLE loc (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES files(id),
    lang TEXT NOT NULL,
    key TEXT NOT NULL,
    line INTEGER NOT NULL,
    value TEXT NOT NULL
);
"""

INDEXES = """
CREATE INDEX idx_files_relpath ON files(relpath);
CREATE INDEX idx_files_source ON files(source_id);
CREATE INDEX idx_defs_key ON defs(key);
CREATE INDEX idx_defs_cat ON defs(category);
CREATE INDEX idx_loc_key ON loc(key);
CREATE INDEX idx_loc_lang ON loc(lang);
"""

# Files whose meaningful keys are nested rather than top level.
DEEP_KEY_DIRS = {
    "common/landed_titles": r"^[ekdcb]_",
    "common/religion/religions": r"^[a-z_]+$",
}

MAX_PARSE_BYTES = 8 * 1024 * 1024


def category_of(relpath: str) -> str:
    parts = relpath.split("/")
    if parts[0] == "common" and len(parts) > 2:
        return "/".join(parts[:2])
    if parts[0] == "history" and len(parts) > 2:
        return "/".join(parts[:2])
    return parts[0]


def _should_parse_defs(relpath: str, ext: str) -> bool:
    if ext != ".txt":
        return False
    return relpath.startswith(("common/", "events/", "history/"))


def build(cfg: Config, verbose: bool = True) -> dict[str, int]:
    cfg.index_db.parent.mkdir(parents=True, exist_ok=True)
    if cfg.index_db.exists():
        cfg.index_db.unlink()
    conn = sqlite3.connect(cfg.index_db)
    conn.executescript(SCHEMA)

    all_sources: list[Source] = playset_sources(cfg)
    known_roots = {s.root.resolve() for s in all_sources}
    for extra in workspace_mods(cfg):
        if extra.root.resolve() not in known_roots:
            all_sources.append(extra)

    started = time.time()
    counts = {"sources": 0, "files": 0, "defs": 0, "loc": 0}

    for source in all_sources:
        if not source.root.is_dir():
            if verbose:
                print(f"  ! missing root, skipped: {source.label} -> {source.root}")
            continue
        cur = conn.execute(
            "INSERT INTO sources (kind, name, mod_id, root, load_order, version, supported_version)"
            " VALUES (?,?,?,?,?,?,?)",
            (
                source.kind,
                source.name,
                source.mod_id,
                str(source.root),
                source.order,
                source.version,
                source.supported_version,
            ),
        )
        source_id = cur.lastrowid
        counts["sources"] += 1
        n_files = n_defs = n_loc = 0

        for relpath, path in iter_files(source.root):
            ext = path.suffix.lower()
            try:
                size = path.stat().st_size
            except OSError:
                continue
            file_id = conn.execute(
                "INSERT INTO files (source_id, relpath, ext, size) VALUES (?,?,?,?)",
                (source_id, relpath, ext, size),
            ).lastrowid
            n_files += 1

            if size > MAX_PARSE_BYTES:
                continue

            if _should_parse_defs(relpath, ext):
                try:
                    text = read_text(path)
                except OSError:
                    continue
                category = category_of(relpath)
                pattern = DEEP_KEY_DIRS.get(category)
                found = keys_matching(text, pattern) if pattern else top_level_defs(text)
                if found:
                    conn.executemany(
                        "INSERT INTO defs (file_id, category, key, line) VALUES (?,?,?,?)",
                        [(file_id, category, key, line) for key, line in found],
                    )
                    n_defs += len(found)

            elif ext == ".yml" and relpath.startswith("localization/"):
                try:
                    text = read_text(path)
                except OSError:
                    continue
                lang, entries, _ = parse_loc(text)
                lang = lang or "unknown"
                if cfg.loc_languages and lang not in cfg.loc_languages:
                    continue
                if entries:
                    conn.executemany(
                        "INSERT INTO loc (file_id, lang, key, line, value) VALUES (?,?,?,?,?)",
                        [(file_id, lang, e.key, e.line, e.value) for e in entries],
                    )
                    n_loc += len(entries)

        conn.commit()
        counts["files"] += n_files
        counts["defs"] += n_defs
        counts["loc"] += n_loc
        if verbose:
            print(f"  [{source.order:>3}] {source.label}: {n_files} files, {n_defs} defs, {n_loc} loc")

    conn.executescript(INDEXES)
    conn.commit()
    conn.close()
    counts["seconds"] = int(time.time() - started)
    return counts


def connect(cfg: Config) -> sqlite3.Connection:
    if not cfg.index_db.is_file():
        raise SystemExit("No index yet. Run: python tools/ck3.py index")
    conn = sqlite3.connect(f"file:{cfg.index_db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def where(cfg: Config, relpath: str) -> list[sqlite3.Row]:
    """Every source providing `relpath`, load order ascending (last one wins)."""
    conn = connect(cfg)
    rows = conn.execute(
        "SELECT s.name, s.kind, s.mod_id, s.load_order, s.root, f.relpath, f.size"
        " FROM files f JOIN sources s ON s.id = f.source_id"
        " WHERE f.relpath = ? OR f.relpath LIKE ?"
        " ORDER BY s.load_order",
        (relpath, f"%{relpath}"),
    ).fetchall()
    conn.close()
    return rows


def find_key(cfg: Config, key: str, exact: bool = True) -> list[sqlite3.Row]:
    conn = connect(cfg)
    if exact:
        clause, params = "d.key = ?", (key,)
    else:
        clause, params = "d.key LIKE ?", (f"%{key}%",)
    rows = conn.execute(
        f"SELECT d.key, d.category, d.line, f.relpath, s.name, s.kind, s.load_order"
        f" FROM defs d JOIN files f ON f.id = d.file_id JOIN sources s ON s.id = f.source_id"
        f" WHERE {clause} ORDER BY s.load_order, f.relpath",
        params,
    ).fetchall()
    conn.close()
    return rows


def find_loc(cfg: Config, key: str, lang: str = "english", exact: bool = True) -> list[sqlite3.Row]:
    conn = connect(cfg)
    clause = "l.key = ?" if exact else "l.key LIKE ?"
    param = key if exact else f"%{key}%"
    rows = conn.execute(
        f"SELECT l.key, l.value, l.line, f.relpath, s.name, s.load_order"
        f" FROM loc l JOIN files f ON f.id = l.file_id JOIN sources s ON s.id = f.source_id"
        f" WHERE {clause} AND l.lang = ? ORDER BY s.load_order",
        (param, lang),
    ).fetchall()
    conn.close()
    return rows


def conflicts(cfg: Config, ignore_base: bool = True) -> list[tuple[str, list[sqlite3.Row]]]:
    """Relative paths claimed by 2+ mods (vanilla excluded, base mod optional).

    Mod-vs-mod collisions are the real compatibility risk; a submod overriding
    its own base mod is expected and filtered out by default.
    """
    conn = connect(cfg)
    excluded = ["vanilla"]
    query = (
        "SELECT f.relpath, s.name, s.mod_id, s.load_order FROM files f"
        " JOIN sources s ON s.id = f.source_id"
        " WHERE s.kind != 'vanilla'"
    )
    params: list[object] = []
    if ignore_base and cfg.base_mod_id:
        query += " AND (s.mod_id IS NULL OR s.mod_id != ?)"
        params.append(cfg.base_mod_id)
    query += " ORDER BY f.relpath, s.load_order"
    grouped: dict[str, list[sqlite3.Row]] = {}
    for row in conn.execute(query, params):
        grouped.setdefault(row["relpath"], []).append(row)
    conn.close()
    _ = excluded
    return [(rel, rows) for rel, rows in sorted(grouped.items()) if len(rows) > 1]


def stats(cfg: Config) -> dict[str, int]:
    conn = connect(cfg)
    out = {
        "sources": conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
        "files": conn.execute("SELECT COUNT(*) FROM files").fetchone()[0],
        "defs": conn.execute("SELECT COUNT(*) FROM defs").fetchone()[0],
        "loc": conn.execute("SELECT COUNT(*) FROM loc").fetchone()[0],
    }
    conn.close()
    return out
