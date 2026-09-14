import re, sys, json, pathlib

P = pathlib.Path("D:/ck3/_gamestate")
WANT = set(sys.argv[1:])
id_rx = re.compile(r"^(\d+)=\{\s*$")
fields = {
    "first_name": re.compile(r"^\tfirst_name=\"(.+)\""),
    "birth": re.compile(r"^\tbirth=([\d.]+)"),
    "nick": re.compile(r"^\tnickname_text=\"(.+)\""),
    "house": re.compile(r"^\tdynasty_house=(\d+)"),
    "skill": re.compile(r"^\tskill=\{ (.+) \}"),
    "culture": re.compile(r"^\tculture=(\d+)"),
    "faith": re.compile(r"^\tfaith=(\d+)"),
    "gold": re.compile(r"^\t\t\tvalue=([\d.]+)"),
    "strength": re.compile(r"^\t\tstrength=(\d+)"),
    "domain": re.compile(r"^\t\tdomain=\{ (.+) \}"),
    "liege": re.compile(r"^\t\tliege=(\d+)"),
    "vassals": re.compile(r"^\t\tvassals_towards_limit=(\d+)"),
    "dread": re.compile(r"^\t\tdread=([\d.]+)"),
    "prestige": re.compile(r"^\t\t\tcurrency=([\d.]+)"),
}
cur = None
out = {}
with open(P, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        m = id_rx.match(line)
        if m:
            cur = m.group(1) if m.group(1) in WANT else None
            continue
        if not cur:
            continue
        for k, rx in fields.items():
            m = rx.match(line)
            if m and k not in out.setdefault(cur, {}):
                out[cur][k] = m.group(1)
                break
for i in sys.argv[1:]:
    print(i, out.get(i))
