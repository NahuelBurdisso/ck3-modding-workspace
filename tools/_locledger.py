"""One-shot: rebuild the phrase ledger from the pre-split loc file in git.

Supersedes the per-line quote pairing in _locdedupe.py, which was wrong: a
phrase wraps across comment lines, so the first quote on a wrapped line closes
the phrase the previous line opened. Pairing per line therefore inverts for the
rest of that line and captures the `, ` separators as phrases. Blocks are joined
into one string before any quote is paired.
"""

import io
import re
import subprocess

REPO = "D:/ck3/mods/battle_chronicles"
DOC = "D:/ck3/docs/battle-chronicles/phrase-ledger.md"
REL = "localization/english/bc_l_english.yml"

COMMENT = re.compile(r"^#")
LEDGER = re.compile(r'", "|^# "|", *$')


def classify(lines):
    hit = [bool(COMMENT.match(l) and l.count('"') >= 2 and LEDGER.search(l)) for l in lines]
    out = list(hit)
    last = None
    for i, h in enumerate(hit):
        if not h:
            continue
        if last is not None and i - last > 1:
            gap = lines[last + 1 : i]
            if gap and all(COMMENT.match(g) and '"' in g for g in gap):
                for m in range(last + 1, i):
                    out[m] = True
        last = i
    # A block's first line usually OPENS with the tail of a phrase that began on
    # the line above - `... after him", "the shape an order has", ...`. That line
    # carries one quote, so it is not a hit and was not bridged, and without it
    # the block's quotes pair on the separators instead of the phrases. Walk the
    # start of every block back over quote-bearing comment lines.
    for i in range(len(out)):
        if not out[i] or (i and out[i - 1]):
            continue
        m = i - 1
        while m >= 0 and COMMENT.match(lines[m]) and '"' in lines[m] and not out[m]:
            out[m] = True
            m -= 1
    return out


def heading_for(lines, start):
    head = []
    i = start - 1
    while i >= 0 and COMMENT.match(lines[i]) and lines[i].strip() != "#" and len(head) < 4:
        head.append(lines[i].lstrip("# ").rstrip())
        i -= 1
    return list(reversed(head))


raw = subprocess.run(
    ["git", "-C", REPO, "show", "HEAD:" + REL], capture_output=True
).stdout.decode("utf-8-sig")
lines = raw.split("\n")
flag = classify(lines)

blocks = []
i = 0
while i < len(lines):
    if flag[i]:
        j = i
        while j < len(lines) and flag[j]:
            j += 1
        body = " ".join(lines[m].lstrip("# ").rstrip() for m in range(i, j))
        # Any fragment before the first quote is the tail of a phrase whose
        # opening lies outside the block. Dropping it is what keeps the pairing
        # aligned to phrases rather than to the `", "` separators between them.
        if '"' in body:
            body = body[body.index('"') :]
        blocks.append({"line": i + 1, "ctx": heading_for(lines, i), "body": body})
        i = j
    else:
        i += 1

seen = {}
total = 0
for n, b in enumerate(blocks, 1):
    b["n"] = n
    b["new"] = []
    for p in re.findall(r'"([^"]+)"', b["body"]):
        p = " ".join(p.split())
        if len(p) < 3:
            continue
        total += 1
        key = p.lower().strip(" .,;:")
        if key in seen:
            continue
        seen[key] = n
        b["new"].append(p)

uniq = sum(len(b["new"]) for b in blocks)

out = [
    "# Battle Chronicles - spent-phrase ledger",
    "",
    "Every phrase already spent in the mod's prose. Check here before writing a",
    "new one; `grep -i` is the intended interface.",
    "",
    "This was 72,263 comment lines inside `bc_l_english.yml`, a file holding 1,344",
    "keys. CK3 discards comments, so none of it was ever read by the game. It held",
    "%s phrase instances of %s distinct phrases, because each batch restated"
    % (f"{total:,}", f"{uniq:,}"),
    "the whole spent list instead of appending to it.",
    "",
    "A phrase is filed under the block that **introduced** it, so a heading reads",
    'as "what this batch added", not "what it had available" - for the latter,',
    "every block above also applies. The yml keeps each block's explanatory",
    "comment and points here by number.",
    "",
]
for b in blocks:
    # Every block gets an entry even when it introduced nothing, because the yml
    # points here by number and a missing heading reads as a lost ledger rather
    # than as a batch that only restated what it already had.
    if not b["new"]:
        out.append("## Block %d - nothing new (yml line %d)" % (b["n"], b["line"]))
        out.append("")
        out.append("Restates phrases already listed above.")
        out.append("")
        continue
    out.append("## Block %d - %d introduced (yml line %d)" % (b["n"], len(b["new"]), b["line"]))
    out.append("")
    for c in b["ctx"]:
        out.append("> " + c)
    if b["ctx"]:
        out.append("")
    out.extend('- "%s"' % p for p in b["new"])
    out.append("")

io.open(DOC, "w", encoding="utf-8", newline="\n").write("\n".join(out).rstrip() + "\n")
print("blocks %d | instances %d | unique %d" % (len(blocks), total, uniq))
