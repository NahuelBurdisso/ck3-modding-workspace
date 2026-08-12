#!/usr/bin/env python3
"""ck3 - command line for the CK3 modding workspace.

    python tools/ck3.py doctor                  check paths and tooling
    python tools/ck3.py index                   (re)build the script index
    python tools/ck3.py stats                   index size
    python tools/ck3.py where common/traits/00_traits.txt
    python tools/ck3.py find brave              where a key is defined
    python tools/ck3.py loc trait_brave         localization lookup
    python tools/ck3.py conflicts               mod-vs-mod file collisions
    python tools/ck3.py new "My Mod" --agot     scaffold a mod
    python tools/ck3.py validate my_mod         static checks
    python tools/ck3.py deploy my_mod           write the <user>/mod pointer
    python tools/ck3.py playset list|add|remove|move|audit
    python tools/ck3.py sync-workshop 3664900993
    python tools/ck3.py launch                  run ck3.exe -debug_mode
    python tools/ck3.py errors                  collect error output
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ck3lib import index as idx  # noqa: E402
from ck3lib import launch as run  # noqa: E402
from ck3lib import playset as ps  # noqa: E402
from ck3lib import scaffold, validate  # noqa: E402
from ck3lib.paths import load_config  # noqa: E402
from ck3lib.scaffold import slugify  # noqa: E402
from ck3lib.sources import playset_sources, workspace_mods  # noqa: E402


def resolve_mod(cfg, name: str) -> Path:
    candidate = Path(name)
    if candidate.is_dir() and (candidate / "descriptor.mod").is_file():
        return candidate.resolve()
    candidate = cfg.mods_src / name
    if candidate.is_dir():
        return candidate
    candidate = cfg.mods_src / slugify(name)
    if candidate.is_dir():
        return candidate
    raise SystemExit(f"no mod named `{name}` in {cfg.mods_src}")


def cmd_doctor(cfg, args) -> int:
    problems = cfg.check()
    print(f"workspace : {cfg.workspace_dir}")
    print(f"game      : {cfg.game_root}")
    print(f"user      : {cfg.user_dir}")
    print(f"workshop  : {cfg.workshop_dir}")
    print(f"exe       : {cfg.exe}  {'ok' if cfg.exe.is_file() else 'MISSING'}")
    print(f"index     : {cfg.index_db}  {'ok' if cfg.index_db.is_file() else 'not built'}")
    playset = playset_sources(cfg, include_vanilla=False)
    print(f"playset   : {len(playset)} mods enabled")
    missing = [s.label for s in playset if not s.root.is_dir()]
    if missing:
        problems.extend(f"enabled mod content missing: {m}" for m in missing)
    print(f"workspace mods: {len(workspace_mods(cfg))}")
    for problem in problems:
        print(f"  ! {problem}")
    return 1 if problems else 0


def cmd_index(cfg, args) -> int:
    print("indexing (vanilla + enabled playset + workspace mods)...")
    counts = idx.build(cfg, verbose=not args.quiet)
    print(
        f"done in {counts['seconds']}s: {counts['sources']} sources, {counts['files']} files, "
        f"{counts['defs']} defs, {counts['loc']} loc keys"
    )
    return 0


def cmd_stats(cfg, args) -> int:
    for key, value in idx.stats(cfg).items():
        print(f"{key:8} {value}")
    return 0


def cmd_where(cfg, args) -> int:
    rows = idx.where(cfg, args.relpath)
    if not rows:
        print("no source provides that path")
        return 1
    for row in rows:
        full = str(Path(row["root"]) / row["relpath"]).replace("\\", "/")
        print(f"[{row['load_order']:>3}] {row['kind']:8} {row['name']}  ({row['size']} bytes)")
        print(f"      {full}")
    print(f"\nwinner: {rows[-1]['name']}")
    return 0


def cmd_find(cfg, args) -> int:
    rows = idx.find_key(cfg, args.key, exact=not args.partial)
    if not rows:
        print("not found (try --partial)")
        return 1
    for row in rows:
        print(f"[{row['load_order']:>3}] {row['name']:<40} {row['relpath']}:{row['line']}  {row['key']}")
    return 0


def cmd_loc(cfg, args) -> int:
    rows = idx.find_loc(cfg, args.key, lang=args.lang, exact=not args.partial)
    if not rows:
        print("not found (try --partial or --lang)")
        return 1
    for row in rows:
        print(f"[{row['load_order']:>3}] {row['name']:<40} {row['relpath']}:{row['line']}")
        print(f"      {row['key']} = {row['value'][:160]}")
    return 0


def cmd_conflicts(cfg, args) -> int:
    collisions = idx.conflicts(cfg, ignore_base=not args.include_base)
    if not collisions:
        print("no mod-vs-mod file collisions")
        return 0
    for relpath, rows in collisions:
        names = " -> ".join(row["name"] for row in rows)
        print(f"{relpath}\n      {names}")
    print(f"\n{len(collisions)} colliding file(s). Last mod in each chain wins.")
    return 0


def cmd_new(cfg, args) -> int:
    mod_root = scaffold.create_mod(
        cfg,
        args.name,
        slug=args.slug,
        tags=args.tags,
        depend_on_base=args.agot,
        git=not args.no_git,
    )
    print(f"created {mod_root}")
    if args.deploy:
        print(f"deployed {scaffold.deploy(cfg, mod_root)}")
    return 0


def cmd_validate(cfg, args) -> int:
    targets = [resolve_mod(cfg, name) for name in args.mods] if args.mods else [m.root for m in workspace_mods(cfg)]
    if not targets:
        print("nothing to validate")
        return 0
    worst = 0
    for mod_root in targets:
        issues = validate.validate_mod(cfg, mod_root, strict=args.strict)
        counts = validate.summarize(issues)
        print(f"\n=== {mod_root.name} ===")
        for issue in issues:
            if issue.level == validate.INFO and not args.verbose:
                continue
            print("  " + issue.format())
        print(f"  {counts[validate.ERROR]} errors, {counts[validate.WARN]} warnings")
        worst = max(worst, 1 if counts[validate.ERROR] else 0)
    return worst


def cmd_deploy(cfg, args) -> int:
    for name in args.mods:
        mod_root = resolve_mod(cfg, name)
        print(f"deployed {scaffold.deploy(cfg, mod_root)}")
    return 0


def cmd_sync_workshop(cfg, args) -> int:
    for mod_id in args.ids:
        print(f"wrote {scaffold.sync_workshop_pointer(cfg, mod_id)}")
    return 0


def cmd_playset(cfg, args) -> int:
    if args.action == "list":
        for pos, rel, name in ps.entries(cfg):
            print(f"[{pos:>3}] {name:<50} {rel}")
        return 0
    if args.action == "audit":
        problems = ps.audit(cfg)
        for problem in problems:
            print(f"  ! {problem}")
        print(f"{len(problems)} problem(s)")
        return 1 if problems else 0
    if args.action == "add":
        print(f"added {ps.add(cfg, args.target, args.position)} (backup written)")
        return 0
    if args.action == "remove":
        print(f"removed {ps.remove(cfg, args.target)} (backup written)")
        return 0
    if args.action == "move":
        if args.position is None:
            raise SystemExit("move needs --position")
        print(f"moved {ps.move(cfg, args.target, args.position)} (backup written)")
        return 0
    raise SystemExit(f"unknown action {args.action}")


def cmd_launch(cfg, args) -> int:
    if args.clear_logs:
        print(f"cleared {run.clear_game_logs(cfg)} old log file(s)")
    capture = run.launch(cfg, debug=not args.no_debug)
    print(f"launched {cfg.exe.name}; stdout -> {capture}")
    print("Steam must be running. Full AGOT stack takes minutes to load and settles near 15 GB RAM.")
    return 0


def cmd_errors(cfg, args) -> int:
    collected = run.collect_errors(cfg, tail=args.tail)
    if not collected:
        print("no logs found")
        return 0
    empty = True
    for name, lines in collected.items():
        print(f"\n=== {name} ({len(lines)} line(s)) ===")
        for line in lines:
            print("  " + line)
        empty = empty and not lines
    if empty:
        print("\nNo error output. For CK3 that means a clean run.")
    return 0


def cmd_probe(cfg, args) -> int:
    collected = run.probe(cfg, args.pattern, ignore_case=args.ignore_case)
    if not collected:
        print(f"no lines matching {args.pattern!r} in {cfg.game_logs}")
        print("debug_log output lands in debug.log, and only after the game has run.")
        return 1
    for name, counts in collected.items():
        total = sum(counts.values())
        print(f"\n=== {name} ({total} hit(s), {len(counts)} distinct) ===")
        for message, hits in counts.most_common():
            print(f"  {hits:>5}  {message}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ck3", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor").set_defaults(func=cmd_doctor)

    p = sub.add_parser("index", help="rebuild the script index")
    p.add_argument("-q", "--quiet", action="store_true")
    p.set_defaults(func=cmd_index)

    sub.add_parser("stats").set_defaults(func=cmd_stats)

    p = sub.add_parser("where", help="which sources ship a file, in load order")
    p.add_argument("relpath")
    p.set_defaults(func=cmd_where)

    p = sub.add_parser("find", help="where a script key is defined")
    p.add_argument("key")
    p.add_argument("--partial", action="store_true")
    p.set_defaults(func=cmd_find)

    p = sub.add_parser("loc", help="localization lookup")
    p.add_argument("key")
    p.add_argument("--lang", default="english")
    p.add_argument("--partial", action="store_true")
    p.set_defaults(func=cmd_loc)

    p = sub.add_parser("conflicts", help="files claimed by 2+ mods")
    p.add_argument("--include-base", action="store_true", help="do not filter out the configured base mod")
    p.set_defaults(func=cmd_conflicts)

    p = sub.add_parser("new", help="scaffold a mod")
    p.add_argument("name")
    p.add_argument("--slug")
    p.add_argument("--tags", nargs="*", default=None)
    p.add_argument("--agot", action="store_true", help="declare a dependency on the configured base mod")
    p.add_argument("--deploy", action="store_true")
    p.add_argument("--no-git", action="store_true")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("validate", help="static checks on a mod folder")
    p.add_argument("mods", nargs="*")
    p.add_argument("--strict", action="store_true", help="also flag definitions with no localization")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("deploy", help="write <user>/mod/<slug>.mod")
    p.add_argument("mods", nargs="+")
    p.set_defaults(func=cmd_deploy)

    p = sub.add_parser("sync-workshop", help="regenerate ugc_<id>.mod pointers")
    p.add_argument("ids", nargs="+")
    p.set_defaults(func=cmd_sync_workshop)

    p = sub.add_parser("playset", help="inspect and edit dlc_load.json")
    p.add_argument("action", choices=["list", "add", "remove", "move", "audit"])
    p.add_argument("target", nargs="?")
    p.add_argument("--position", type=int)
    p.set_defaults(func=cmd_playset)

    p = sub.add_parser("launch", help="start ck3.exe and capture stdout")
    p.add_argument("--no-debug", action="store_true")
    p.add_argument("--clear-logs", action="store_true")
    p.set_defaults(func=cmd_launch)

    p = sub.add_parser("errors", help="collect error output from the last run")
    p.add_argument("--tail", type=int, default=80)
    p.set_defaults(func=cmd_errors)

    p = sub.add_parser("probe", help="count debug_log markers in the game logs")
    p.add_argument("pattern", help="regex, e.g. 'BC:' to aggregate one mod's markers")
    p.add_argument("-i", "--ignore-case", action="store_true")
    p.set_defaults(func=cmd_probe)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config()
    return args.func(cfg, args)


if __name__ == "__main__":
    raise SystemExit(main())
