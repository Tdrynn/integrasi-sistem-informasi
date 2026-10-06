# **Tugas Analisis Minggu 3**
---
## **1. Analisis Pola Arsitektur**
---

Rancangan ini disebut sebagai **Adapter Pattern** disebabkan oleh `adapter_service.py` yang berperan sebagai perantara antara klien modern/web dengan sistem legacy yang menggunakan `students_db.txt`. Klien tidak perlu mengetahui bagaimana sistem legacy menyimpan atau mengelola data. Klien cukup berkomunikasi menggunakan HTTP dan XML, misalnya `GET /students/2415354001` atau `POST /students`, sedangkan adapter menerjemahkan permintaan tersebut menjadi operasi terhadap berkas teks.

**Keuntungan bagi klien web luar**:
- **Loose coupling**: Klien hanya perlu tahu kontrak data (endpoint dan skema XML), bukan lokasi, nama file, atau format delimiter koma di basis data legacy.
- **Akses lewat protokol standar**: Klien bisa memakai `curl`, browser, atau Postman tanpa harus bisa membaca file teks lokal.
- **Pesan error terstruktur**: Klien mendapat respons yang jelas seperti 404, bukan perilaku mentah dari program C.


---
## **2. Analisis Overhead Serialisasi Data**
---
Respons dari `GET /students/2415354001`:

```
<?xml version='1.0' encoding='utf-8'?>
<StudentResponse><NIM>2415354001</NIM><Nama>I Made Sujana</Nama><Jurusan>Teknologi Informasi</Jurusan><Status>ACTIVE</Status></StudentResponse>
```

### Jumlah karakter/byte dari data aktual:
**Data** | **byte** |
--- | ---
2415354001 | 10 |
I Made Sujana | 13 |
Teknologi Informasi | 19 |
ACTIVE | 6 |
**Total** | 48 byte |

### Jumlah byte dari respons XML:
**Komponen** | **byte** |
--- | ---
Deklarasi XML + newline (`<?xml version='1.0' encoding='utf-8'?>` = 38, newline = 1) | 39 |
`<StudentResponse>` + `</StudentResponse>` (17 + 18) | 35 |
`<NIM>` + `</NIM>` (5 + 6) | 11 |
`<Nama>` + `</Nama>` (6 + 7) | 13 |
`<Jurusan>` + `</Jurusan>` (9 + 10) | 19 |
`<Status>` + `</Status>` (8 + 9) | 17 |
**Data aktual** | 48 |
**Total** | 182 byte |

## Rasio overhead
overhead = 182 - 48 = **134 byte**
- Terhadap total respons: 134 / 182 * 100% = **73,6%**
- Terhadap data aktual: 134 / 48 * 100% = **279,2%**

Sekitar 3/4 ukuran respons hanyalah struktur (tag dan deklarasi), dan hanya sekitar 26% data sebenarnya. Sebagai pembanding, baris yang sama pada file legacy hanya 51 byte, jadi pada XML ukurannya sekitar 3,5 kali lebih besar dengan catatan ukuran header HTTP tidak dihitung.

## **3. Prediksi Keterbatasan Integrasi**
---

### Apa yang terjadi pada 500 POST simultan?
`HTTPServer` bawaan Python bersifat *single-threaded* dan memproses satu permintaan dalam satu waktu. Jika terdapat 500 permintaan `POST` secara simultan,  dampaknya adalah server tidak akan sanggup membuka banyak koneksi secara bersamaan, yang menyebabkan koneksi bisa ditolak atau timeout.

Jika server diganti `ThreadingHTTPServer`
`ThereadingHTTPServer` membuat satu thread baru untuk setiap permintaan, sehingga 500 permintaan POST diproses hampir bersamaan dan tidak lagi antre satu per satu. Masalahnya, `students_db.txt` hanyalah berkas teks biasa tanpa mekanisme *locking*, sehingga semua thread menulis ke file yang sama tanpa koordinasi. Dampaknya:
- Terjadi race condition: baris bisa saling menimpa atau tercampur, sehingga file tidak lagi sesuai format 4 kolom dan data rusak.
- Tidak ada validasi duplikasi NIM, sehingga data yang sama bisa tercatat berulang.
- Tidak ada mekanisme *retry* atau konfirmasi pengiriman jika penulisan gagal di tengah jalan.

### Mengapa Message Broker dibutuhkan?
Message Broker seperti RabbitMQ atau Kafka menyelesaikan masalah yang terjadi dengan cara:
- **Buffering**: Lonjakan 500 permintaan POST akan ditampung di antrean dan tidak ditolak.
- **Decoupling**: Pengirim tidak perlu menunggu legacy selesai menulis (asinkron).
- **Durabilitas dan retry**: Pesan disimpan sampai berhasil diproses, sehingga tidak hilang saat terjadi kegagalan.
- **Skalabilitas**: Jumlah producer bisa bertambah tanpa mengubah cara legacy diakses.