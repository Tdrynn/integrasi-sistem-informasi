import threading
import urllib.request
import urllib.error
import time
from collections import Counter

URL = "http://localhost:8000/students"
N = 500

barrier = threading.Barrier(N)
results = []
lock = threading.Lock()

def send(i):
    nim = f"2415354{i:03d}"
    body = (
        f"<StudentRequest><NIM>{nim}</NIM><Nama>Tes {i}</Nama>"
        f"<Jurusan>Uji Beban</Jurusan><Status>ACTIVE</Status></StudentRequest>"
    ).encode()
    req = urllib.request.Request(
        URL, data=body, headers={"Content-Type": "application/xml"}, method="POST"
    )
    barrier.wait()
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            res = r.status
    except urllib.error.HTTPError as e:
        res = e.code
    except Exception as e:
        res = type(e).__name__
    with lock:
        results.append(res)

start = time.time()
threads = [threading.Thread(target=send, args=(i,)) for i in range(N)]
for t in threads: t.start()
for t in threads: t.join()

print(f"Selesai dalam {time.time() - start:.2f} detik")
print("Hasil respons:", dict(Counter(results)))