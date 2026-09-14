import json, re, sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DD = Path(r"D:/Documents/Paradox Interactive/Crusader Kings III")
WS = Path(r"D:/SteamLibrary/steamapps/workshop/content/1158310")
ACF = Path(r"D:/SteamLibrary/steamapps/workshop/appworkshop_1158310.acf")

# from memory: deliberate exclusions and their reasons
SKIP = {
    "3350459101": "Color Picker+ — broken by CBO 0.5.0",
    "3081701005": "CoA Rally Points — broken 1.18 map_icon_layer.gui",
    "3525365211": "More Bloodlines — overrides window_character.gui, THE crash file",
    "3522779004": "Bloodlines: Legacies — 158 collisions with Brightboar, redundant",
    "3328141802": "Armies of Westeros REMASTERED — replaces the AoW already installed",
    "3403938445": "Legacy of Valyria — user chose to skip",
    "3719888822": "LoV 0.5.1 rebuild compatch — only useful with LoV",
    "3471463581": "Fix Travel Route UI — same gui file as Route Planner Plus, never both",
    "3009868580": "Travel Speed — ships whole 00_defines.txt, clobbers every AGOT define",
    "3044702235": "Slightly Faster Travel — same defines problem",
    "3463729959": "Spanish translation — game is English",
}
PENDING11 = {
    "3664900993": "Nobility of Westeros", "3742055253": "NoW compatch",
    "3753608966": "NoW compatch", "3083111367": "Revive Dead House",
    "3466228580": "More Dragon Events", "3621472324": "Great Councils",
    "3586934156": "Unbound", "3496313878": "Knights & Banners",
    "3692879370": "Landmarks of Westeros", "3697008412": "Landmarks COW compatch",
    "3450300304": "Sundry",
}

def modname(d):
    cands = list(d.glob("descriptor.mod")) + list(d.glob("*.mod"))
    for c in cands:
        t = c.read_text(encoding="utf-8-sig", errors="replace")
        m = re.search(r'^name\s*=\s*"([^"]+)"', t, re.M)
        s = re.search(r'^supported_version\s*=\s*"([^"]+)"', t, re.M)
        if m:
            return m.group(1), (s.group(1) if s else "?")
    return "(no descriptor)", "?"

# --- enabled -----------------------------------------------------------------
dlc = json.loads((DD / "dlc_load.json").read_text(encoding="utf-8-sig"))
enabled_rel = dlc["enabled_mods"]
enabled_ids = {m.group(1) for r in enabled_rel if (m := re.search(r"ugc_(\d+)\.mod", r))}
local_enabled = [r for r in enabled_rel if "ugc_" not in r]
print(f"enabled: {len(enabled_rel)}  (workshop {len(enabled_ids)}, local {len(local_enabled)})")
print("  local:", ", ".join(r.replace("mod/", "") for r in local_enabled))

# --- on disk -----------------------------------------------------------------
on_disk = {d.name: modname(d) for d in WS.iterdir() if d.is_dir()}
print(f"workshop folders on disk: {len(on_disk)}")

# --- acf (what Steam thinks is subscribed) -----------------------------------
acf_ids, acf_time = set(), {}
if ACF.exists():
    txt = ACF.read_text(encoding="utf-8", errors="replace")
    body = txt.split('"WorkshopItemsInstalled"', 1)[-1]
    for m in re.finditer(r'"(\d{9,10})"\s*\{(.*?)\n\t\t\}', body, re.S):
        acf_ids.add(m.group(1))
        tu = re.search(r'"timeupdated"\s*"(\d+)"', m.group(2))
        if tu:
            acf_time[m.group(1)] = int(tu.group(1))
print(f"acf installed entries: {len(acf_ids)}")

missing_folder = sorted(acf_ids - set(on_disk))
if missing_folder:
    print("  !! in acf but NO folder (unsubscribed mid-flight / not downloaded):", missing_folder)

# --- the delta ---------------------------------------------------------------
not_enabled = sorted(set(on_disk) - enabled_ids,
                     key=lambda i: -acf_time.get(i, 0))
print(f"\n=== ON DISK BUT NOT ENABLED: {len(not_enabled)} ===")
for i in not_enabled:
    name, sup = on_disk[i]
    when = datetime.fromtimestamp(acf_time[i]).strftime("%Y-%m-%d") if i in acf_time else "?"
    tag = ""
    if i in SKIP:
        tag = "  SKIP: " + SKIP[i]
    elif i in PENDING11:
        tag = "  [one of the 11 that crashed as a set]"
    print(f"  {i:11} {when}  {name[:46]:46} sup={sup:10}{tag}")

ghosts = sorted(enabled_ids - set(on_disk))
if ghosts:
    print("\n!! ENABLED BUT NO FOLDER (dangling pointer):", ghosts)

unknown = [i for i in not_enabled if i not in SKIP and i not in PENDING11]
print(f"\nsummary: {len(not_enabled)} disabled-on-disk = "
      f"{len([i for i in not_enabled if i in SKIP])} deliberate skips + "
      f"{len([i for i in not_enabled if i in PENDING11])} of the crashing 11 + "
      f"{len(unknown)} unclassified")
print("unclassified (candidates for a new batch):")
for i in unknown:
    when = datetime.fromtimestamp(acf_time[i]).strftime("%Y-%m-%d %H:%M") if i in acf_time else "?"
    print(f"  {i:11} {when}  {on_disk[i][0][:50]}")
