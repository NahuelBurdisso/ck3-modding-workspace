import sys, zipfile, io, pathlib

p = pathlib.Path(sys.argv[1])
data = p.read_bytes()
i = data.find(b"PK\x03\x04")
print("PK offset:", i, "size:", len(data))
if i < 0:
    print("no zip; plain text save")
    sys.exit()
print(data[:i].decode("utf-8", "replace")[:1500])
z = zipfile.ZipFile(io.BytesIO(data[i:]))
print("members:", z.namelist())
out = pathlib.Path("D:/ck3/_gamestate")
with z.open(z.namelist()[0]) as f, open(out, "wb") as o:
    while True:
        b = f.read(1 << 20)
        if not b:
            break
        o.write(b)
print("extracted", out, out.stat().st_size)
