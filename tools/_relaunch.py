"""Archive logs, close ck3.exe, verify dlc_load.json, relaunch the game.

Called before a monitored run. Everything here has bitten before:
 * tasklist/taskkill must be invoked with an argv list -- git-bash mangles `/FI` into
   `C:/Program Files/Git/FI`.
 * ask ck3.exe to close first and only force after a grace period; it lingers ~20s at
   several GB after the window goes away.
 * the Paradox Launcher must stay closed. It regenerates dlc_load.json from
   launcher-v2.sqlite within seconds and wipes hand edits.
"""
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DD = Path(r"D:/Documents/Paradox Interactive/Crusader Kings III")
EXE = Path(r"D:/SteamLibrary/steamapps/common/Crusader Kings III/binaries/ck3.exe")
TAG = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d-%H%M%S")


def alive():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ck3.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    return "ck3.exe" in out


crashes = sorted(p.name for p in (DD / "crashes").iterdir()) if (DD / "crashes").is_dir() else []
print(f"crash dirs before: {len(crashes)}")

if alive():
    print("closing ck3.exe (graceful)...")
    subprocess.run(["taskkill", "/IM", "ck3.exe"], capture_output=True, text=True)
    for _ in range(30):
        if not alive():
            break
        time.sleep(2)
    if alive():
        print("still up after 60s -- forcing")
        subprocess.run(["taskkill", "/F", "/IM", "ck3.exe"], capture_output=True, text=True)
        for _ in range(15):
            if not alive():
                break
            time.sleep(2)
    print("closed" if not alive() else "WARNING: still running")
else:
    print("ck3.exe was not running")

arch = DD / "logs" / f"archive_{TAG}"
arch.mkdir(parents=True, exist_ok=True)
for name in ("error.log", "debug.log", "system.log", "gui_warnings.log"):
    src = DD / "logs" / name
    if src.is_file():
        shutil.copy2(src, arch / name)
        src.unlink()
        print(f"archived+cleared {name}")
print("archive:", arch)

dl = json.loads((DD / "dlc_load.json").read_text(encoding="utf-8"))
mods = dl["enabled_mods"]
print(f"enabled_mods: {len(mods)}")
for i, m in enumerate(mods):
    if "rpp_119_fix" in m:
        print(f"  rpp_119_fix present at [{i}]")
missing = [m for m in mods if not (DD / m).is_file()]
print(f"dangling pointers: {len(missing)}", missing[:5])
if missing:
    raise SystemExit("refusing to launch with dangling pointers")

print("launching", EXE)
subprocess.Popen([str(EXE)], cwd=str(EXE.parent))
for _ in range(30):
    time.sleep(2)
    if alive():
        print("ck3.exe is up")
        break
else:
    raise SystemExit("ck3.exe never appeared")
