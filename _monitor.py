import subprocess, time, re, os
from pathlib import Path
from datetime import datetime

DD = Path(r"D:/Documents/Paradox Interactive/Crusader Kings III")
ERR = DD / "logs/error.log"
DBG = DD / "logs/debug.log"
CRASHES = DD / "crashes"

BASE_CRASHES = {p.name for p in CRASHES.iterdir()} if CRASHES.is_dir() else set()

def rss_mb():
    out = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq ck3.exe", "/FO", "CSV", "/NH"],
        capture_output=True, text=True
    ).stdout
    m = re.search(r'"([\d.,]+) K', out)
    if not m:
        return None
    return int(re.sub(r"[.,]", "", m.group(1))) // 1024

t0 = time.time()
frontend_at = None
seen_alive = False
DEADLINE = 35 * 60
# `frontend_main.gui` appears in debug.log DURING loading, not at completion, so
# frontend_at is optimistic by several minutes. Require a wall-clock floor too.
MIN_TOTAL = 16 * 60
# files this run is validating -- any parse error naming one is a patch bug
# Keep these SPECIFIC. A loose token here is worse than no token: "ancestors" matched the
# `agot_dna_*_ancestors.txt` gene-warning spam and reported 33 542 "patch-file errors".
PATCH_FILES = ("07_dlc_ep3_scripted_effects", "hud.gui", "color_lists",
               "child_birth_on_actions", "00_challenge_characters",
               "scripted_illustrations/ingame.txt", "agot_d_kingsguard",
               "agot_kingsguard.gui", "season_events", "agot_coa_events",
               "00_agot_kingsguard_triggers", "00_agot_the_seven",
               "agot_silent_sisters_events")

while time.time() - t0 < DEADLINE:
    el = int(time.time() - t0)
    mb = rss_mb()
    new_crash = ({p.name for p in CRASHES.iterdir()} - BASE_CRASHES) if CRASHES.is_dir() else set()

    asserts = ""
    if ERR.is_file():
        try:
            t = ERR.read_text(encoding="utf-8", errors="replace")
            bad = re.findall(r"Assertion failed: ([^\n]{0,70})", t)
            # the benign one AGOT always emits
            real = [b for b in bad if "Achievements not loaded" not in b]
            if real:
                asserts = f"  REAL_ASSERT x{len(real)}: {real[0][:60]}"
            elif bad:
                asserts = f"  (benign achievements assert x{len(bad)})"
        except OSError:
            pass

    fe = ""
    if DBG.is_file() and frontend_at is None:
        try:
            if "frontend_main.gui" in DBG.read_text(encoding="utf-8", errors="replace")[-2_000_000:]:
                frontend_at = el
                fe = "  <-- FRONTEND REACHED"
        except OSError:
            pass

    stamp = datetime.now().strftime("%H:%M:%S")
    if mb is None:
        if seen_alive:
            print(f"[{stamp}] +{el:4}s  PROCESS GONE -- CRASH{asserts}", flush=True)
            if new_crash:
                print(f"           new crash dir: {sorted(new_crash)}", flush=True)
            raise SystemExit(2)
        print(f"[{stamp}] +{el:4}s  not started yet", flush=True)
    else:
        seen_alive = True
        post = f"  frontend+{el - frontend_at}s" if frontend_at is not None else ""
        print(f"[{stamp}] +{el:4}s  {mb:6} MB{post}{fe}{asserts}", flush=True)

    if new_crash:
        print(f"[{stamp}] NEW CRASH DIR: {sorted(new_crash)}", flush=True)
        raise SystemExit(2)

    if frontend_at is not None and el - frontend_at >= 11 * 60 and el >= MIN_TOTAL:
        hits = []
        if ERR.is_file():
            t = ERR.read_text(encoding="utf-8", errors="replace")
            for line in t.splitlines():
                if any(f in line for f in PATCH_FILES) and "[E]" in line:
                    hits.append(line.strip()[:160])
        print(f"\nPASS: alive {el - frontend_at}s past frontend, {el}s total, {mb} MB, no new crash dir.",
              flush=True)
        print(f"patch-file errors in error.log: {len(hits)}", flush=True)
        for h in hits[:15]:
            print("   ", h, flush=True)
        raise SystemExit(0)

    time.sleep(20)

print("\nTIMEOUT: deadline hit without confirming frontend.", flush=True)
raise SystemExit(3)
