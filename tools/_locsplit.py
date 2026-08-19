"""One-shot: lift the spent-phrase ledger out of bc_l_english.yml.

The ledger was 72k of the file's 77k comment lines. CK3 discards comments, so
this changes nothing in game; it exists so a 1,344-key file stops costing 5.6 MB
to open. The phrases themselves go to phrase-ledger.md, deduped, by
`_locledger.py` - this writes the yml side, and shares that module's classifier
so a block number means the same thing in both files.

Reads the pre-split file from git HEAD, so it is safe to re-run. --apply writes.
"""

import io
import re
import subprocess
import sys

sys.path.insert(0, "D:/ck3/tools")
import _locledger as L  # noqa: E402

YML = "D:/ck3/mods/battle_chronicles/localization/english/bc_l_english.yml"
KEY = re.compile(r"^\s+[A-Za-z0-9_.]+:[0-9]* ")


def main():
    apply = "--apply" in sys.argv
    raw = subprocess.run(
        ["git", "-C", L.REPO, "show", "HEAD:" + L.REL], capture_output=True
    ).stdout.decode("utf-8-sig")
    lines = raw.split("\n")
    flag = L.classify(lines)

    kept, blocks = [], 0
    i = 0
    while i < len(lines):
        if flag[i]:
            while i < len(lines) and flag[i]:
                i += 1
            blocks += 1
            kept.append(
                "# SPENT PHRASES: ../../../docs/battle-chronicles/phrase-ledger.md, block %d."
                % blocks
            )
        else:
            kept.append(lines[i])
            i += 1

    before = sum(1 for l in lines if KEY.match(l))
    after = sum(1 for l in kept if KEY.match(l))
    print("lines %d -> %d | blocks %d | keys %d -> %d" % (len(lines), len(kept), blocks, before, after))
    if before != after:
        print("ABORT: key count changed")
        return 1
    if not apply:
        print("(dry run)")
        return 0
    io.open(YML, "w", encoding="utf-8-sig", newline="\n").write("\n".join(kept))
    print("written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
