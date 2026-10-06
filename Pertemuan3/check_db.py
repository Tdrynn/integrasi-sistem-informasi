from collections import Counter

valid, rusak = [], []
with open("students_db.txt") as f:
    for no, line in enumerate(f, 1):
        line = line.rstrip("\n")
        if not line:
            continue
        (valid if len(line.split(",")) == 4 else rusak).append((no, line))

nims = [l.split(",")[0] for _, l in valid if l.startswith("9")]
dup = [n for n, c in Counter(nims).items() if c > 1]

print("Baris valid        :", len(valid))
print("Baris rusak        :", len(rusak))
print("Data uji tercatat  :", len(nims), "dari 500")
print("NIM duplikat       :", len(dup))
for no, l in rusak[:10]:
    print("  rusak di baris", no, "->", l)