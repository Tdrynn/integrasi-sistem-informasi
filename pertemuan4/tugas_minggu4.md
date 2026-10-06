# **Tugas minggu 4**

## Tabel Hasil Pengujian Benchmark
**Jumlah Rekaman** | **Ukuran XML<br>(Bytes)** | **Ukuran JSON<br>(Bytes)** | **Presentase Efisiensi Ukuran<br>(%)** |
--- | --- | --- | --- |
**10 Data** | 1438 | 1166 | 18.92% |
**50 Data** | 7058 | 5826 | 17.46% |
**100 Data** | 14084 | 11652 | 17.27% |
**500 Data** | 70684 | 58652 | 17.02% |

## Analisis Pertanyaan Kritis
---

### 1. Analisis Struktur Payload:
---
Faktor sintaksis yang membuat ukuran Byte pada XML menjadi lebih besar:
- Tag penutup berulang: Setiap elemen ditulis dua kali (`<nama></nama>`). Pada JSON, nama cukup ditulis sekali (`"nama":`).
- Pembungkus per rekaman: XML memerlikan elemen `<student>...</student>` untuk setiap baris data (19 byte), sedangkan JSON cukup `{ }` (2 byte).
- Nama tag panjang dan berulang: Semakin panjang nama field, semakin besar overhead XML, karena nama itu dicetak dua kali per fiel per rekaman.
- Deklarasi dan fitur XML lain: Deklarasi `<?xml ... ?>`, namespace, dan atribut menambah ukuran. Skrip benchmark tidak memakainya, jadi angka di atas masih termasuk perhitungan yang "menguntungkan" XML.


### 2. Analisis Deserialisasi / Parsing di Sisi Klien:
---
**Respons XML:**
1. Terima teks mentah, lalu parse dengan `DOMParser` (atau `XMLHttpRequest.responseXML`) menjadi pohon DOM.
2. Telusuri pohon itu dengan `getElementsByTagName()` atau `querySelector()` untuk mencari node yang dibutuhkan.
3. Ambil nilainya dengan `.textContext`, dan nilai selalu berupa **string**, jadi angka atau boolean harus dikonversi manual.
4. Ubah data ke objek JavaScript sendiri bila ingin dipakai di logika aplikasi atau UI.


**Respons JSON:**
1. Panggil `response.json()` atau `JSON.parse(teks)`.
2. Langsung pakai hasilnya, misalnya `data.data[0].nama`.

**Mengapa ekosistem web beralih ke JSON:**
1. JSON adalah turunan sintaks objek JavaScript, sehingga hasil parsing langsung menjadi objek dan array native tanpa penelusuran DOM.
2. Kode klien lebih sedikit dan lebih mudah dibaca, sehingga resiko bug lebih kecil.
3. Tipe data dasar (angka, boolean, null, array) terjaga, sedangkan XML semuanya teks.
4. Payload lebih ringkas dan parsing biasanya lebih cepat serta hemat memori.
5. Dukungan alat modern sangat luas: `fetch`, Postman, Open API, dan hampir semua bahasa pemrograman

XML tetap relevan untuk dokumen bermarkup, skema ketat (XSD), dan sistem enterprise lama (misalnya SOAP), tetapi untuk REST API modern JSON lebih praktis.


### 3. Bottleneck Arsitektur RESTful Synchronous:
---

**Apa yang tejadi pada 100 POST bersamaan dengan lock 1,5 detik?**
Karena penulisan ke `data.txt` harus bergantian (satu penulis pada satu waktu), 100 permintaan tersebut efektif diproses berurutan:
- Throughput maksimal hanya 1 / 1,5 = **0,67 permintaan/detik**.
- Klien ke-1 selesai di detik 1,5, klien ke-50 di detik 75, dan klien ke-100 baru di detik 150 (2,5 menit). Rata-rata waktu tunggu sekitar 75 detik.
- Sebagian bersar klien akan terkena *timeout*. Misalnya dengan timeout 30 detik, hanya sekitar 20 klien pertama yang berhasil, sisanya gagal walau server masih memprosesnya (klien menyerah, tetapi data bisa tetap tertulis sehingga status tidak jelas).
- Server Flask menahan satu thread dan satu koneksi untuk setiap klien yang menunggu. Thread dan memori menumpuk (*resource exhaustion*), sehingga permintaan GET yang tidak terkait pun ikut melambat atau gagal.
- Jika klien mencoba ulang (*retry*) karena timeout, beban makin besar dan bisa memicu duplikasi data. Pengecekan duplikasi ID di `create_student()` juga rentan balapan karena "baca lalu tulis" tidak atomik.

**Mengapa synchronous blocking di HTTP/1.1 menjadi bottleneck:**
- Satu koneksi TCP hanya melayani **satu permintaan aktif** pada satu waktu (*head-of-line blocking*). Permintaan berikutnya di koneksi yang sama harus menunggu responsnya selesai. Peramban memang membuka beberapa koneksi paralel (sekitar 6 per host), tetapi jumlahnya terbatas.
- Sifatnya *synchronous coupling:* Klien harus menunggu sampai I/O legacy selesai. Kecepatan seluruh sistem ditentukan paling lambat (legacy 1,5 detik), dan klien terikat pada kondisi server hilir.

**Bagaimana gRPC (Minggu 5) mengatasinya:**
- gRPC berjalan di atas **HTTP/2** yang memakai *miltiplexing*: banyak permintaan berjalan bersamaan dalam satu koneksi sebafai stream terpisah, sehingga HoL blocking tingkat HTTP hilang.
- Memakai serialisasi biner Protocol Buffers, yang lebih kecil dan lebih cepat dari JSON.
- Mendukung *streaming, deadline/timeout eksplisit*, dan *flow control*.
- Keterbatasannya: Jika pemanggilannya tetap sinkron dan legacy tetap 1,5 detik per tulis, waktu tunggu klien akan tetap lama. gRPC memperbaiki transport, bukan lambatnya penyimpanan.

**Bagaimana Asynchronous Message Broker (Minggu 6) mengatasinya:**

- API Gateway tidak menunggu penulisan selesai. Ia memasukan permintaan ke antrean lalu langsung membalas `202 Acepted` dalam milidetik, dan ke-100 klien tidak lagi diblokir.
- Satu *consumer* mengambil pesan dari antrean dan menulis ke `data.txt` satu per satu dengan kecepatan legacy (1,5 detik). Penulisan tetap berurutan sehingga file aman, dan lonjakan beban diserap antrean (*buffering / load leveling*).
- Pesan bersifat tahan lama (durable) dan bisa dicoba ulang, dan pesan yang gagal dipindah ke *dead-letter queue*, sehingga data tidak hilang saat terjadi timeout atau kegagalan.
- Klien mengetahui hasil akhir lewat polling status, webhook, atau notifikasi.
- Total waktu pemrosesan tetap 150 detik, tetapi *pengalaman klien dan stabilitas server* berubah drastis: tidak ada koneksi tertahan dan tidak ada timeout massal.