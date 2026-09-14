import re, io, pathlib, sys

P = pathlib.Path("D:/ck3/_gamestate")
CH = 1 << 22


def scan(pat, limit=20, ctx=400):
    """stream-scan the huge gamestate for a regex, return matches with context"""
    rx = re.compile(pat)
    out = []
    prev = ""
    off = 0
    with open(P, "r", encoding="utf-8", errors="replace") as f:
        while True:
            buf = f.read(CH)
            if not buf:
                break
            hay = prev + buf
            for m in rx.finditer(hay):
                out.append((off - len(prev) + m.start(), hay[max(0, m.start() - ctx):m.end() + ctx]))
                if len(out) >= limit:
                    return out
            off += len(buf)
            prev = hay[-4096:]
    return out


if __name__ == "__main__":
    for pat in sys.argv[1:]:
        print("=" * 20, pat)
        for pos, txt in scan(pat):
            print("--- @", pos)
            print(txt)
