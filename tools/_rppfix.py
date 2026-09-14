"""Regenerate gui/window_travel_route_edit.gui from Route Planner Plus' copy.

RPP ships two `visible` statements that call data functions 1.19 removed. The engine
cannot parse them, logs `pdx_gui_factory.cpp:934` and drops the property, so the
"select a province" prompt and the destination highlight are stuck visible and the
route editor is unusable.

This mod ships RPP's own file with those two statements swapped for the 1.19
equivalent. Because it is a whole-file copy it PINS RPP at the version it was built
from -- rerun this after every RPP update, or the mod becomes an update-reverter.

    python tools/_rppfix.py          # report only
    python tools/_rppfix.py --write
"""
import sys
from pathlib import Path

SRC = Path("D:/SteamLibrary/steamapps/workshop/content/1158310/3689519233"
           "/gui/window_travel_route_edit.gui")
DST = Path(__file__).parent.parent / "mods/rpp_119_fix/gui/window_travel_route_edit.gui"

# 1.19 folded the AtBegin/AtEnd pair into one call. `IsSelectingProvinceAt( d, w )`
# still covers the slot before waypoint w; the slot before the destination itself --
# which is what AtEnd meant, and what AtBegin meant while the waypoint list was empty
# -- is now IsSelectingProvinceBeforeDestination( d ). Vanilla uses exactly this pair
# at game/gui/window_travel_route_edit.gui:123 and :136, and they are the only two
# IsSelectingProvince* functions left in the whole game dir.
OLD = (b"Or( TravelRouteEditWindow.IsSelectingProvinceAtEnd( TravelPlanDestination.GetIndex ), "
       b"And( TravelRouteEditWindow.IsSelectingProvinceAtBegin( TravelPlanDestination.GetIndex ), "
       b"IsDataModelEmpty( TravelPlanDestination.GetWaypoints ) ) )")
NEW = b"TravelRouteEditWindow.IsSelectingProvinceBeforeDestination( TravelPlanDestination.GetIndex )"
EXPECTED = 2

src = SRC.read_bytes()
found = src.count(OLD)
print("source:", SRC)
print("  %d bytes, BOM %s, CRLF %d"
      % (len(src), src.startswith(b"\xef\xbb\xbf"), src.count(b"\r\n")))
print("  dead statements found: %d (expected %d)" % (found, EXPECTED))

if found != EXPECTED:
    print("MISMATCH -- RPP changed this file. Re-derive the substitution before writing.")
    raise SystemExit(1)

out = src.replace(OLD, NEW)

# The engine reports gui errors by line number, so the fix must not move any line.
if out.count(b"\n") != src.count(b"\n"):
    print("FAIL: line count changed")
    raise SystemExit(1)
if b"IsSelectingProvinceAtEnd" in out or b"IsSelectingProvinceAtBegin" in out:
    print("FAIL: a dead call survived")
    raise SystemExit(1)

print("  output: %d bytes, %d lines, %d fixed call sites"
      % (len(out), out.count(b"\n"), out.count(NEW)))
print("RESULT: PASS")

if "--write" in sys.argv:
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_bytes(out)
    print("WROTE", DST)
