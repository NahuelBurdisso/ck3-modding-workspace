import re, pathlib, sys

P = pathlib.Path("D:/ck3/_gamestate")
CH = 1 << 22


def extract(anchor_rx, nth=1):
    rx = re.compile(anchor_rx)
    prev = ""
    hits = 0
    with open(P, "r", encoding="utf-8", errors="replace") as f:
        while True:
            buf = f.read(CH)
            if not buf:
                return None
            hay = prev + buf
            for m in rx.finditer(hay):
                hits += 1
                if hits < nth:
                    continue
                # brace match from here, pulling more data as needed
                tail = hay[m.start():]
                depth = 0
                started = False
                acc = []
                while True:
                    for c in tail:
                        acc.append(c)
                        if c == "{":
                            depth += 1
                            started = True
                        elif c == "}":
                            depth -= 1
                            if started and depth == 0:
                                return "".join(acc)
                    tail = f.read(CH)
                    if not tail:
                        return "".join(acc)
            prev = hay[-8192:]


if __name__ == "__main__":
    nth = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    t = extract(sys.argv[1], nth)
    print(t if t else "NOT FOUND")
