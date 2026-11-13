# ListrikKu

Pencatat meteran listrik + estimasi tagihan PLN — CLI Python tanpa
dependensi, data tersimpan lokal sebagai JSON.

Catat angka meteran (kWh) tiap kali sempat, lalu ListrikKu menghitung
pemakaian antar bacaan, rata-rata harian, dan perkiraan tagihan sesuai
tarif rumah tangga PLN yang berlaku. Cocok untuk yang ingin tahu ke mana
larinya kWh tiap bulan — tanpa aplikasi berat, tanpa akun, tanpa biaya.

## Tarif yang dipakai

Tarif rumah tangga PLN Triwulan IV 2026 (Oktober–Desember 2026, sesuai
Permen ESDM No. 7 Tahun 2024; tarif tidak naik dari triwulan sebelumnya):

| Golongan | Daya | Tarif per kWh |
| --- | --- | --- |
| R-1/TR subsidi | 450 VA | Rp415 |
| R-1/TR subsidi | 900 VA | Rp605 |
| R-1/TR (RTM) | 900 VA | Rp1.352 |
| R-1/TR | 1.300 VA | Rp1.444,70 |
| R-1/TR | 2.200 VA | Rp1.444,70 |
| R-2/R-3 | 3.500 VA ke atas | Rp1.699,53 |

Tarif di atas adalah tarif dasar sebelum PPJ (pajak penerangan jalan —
besarnya beda tiap daerah). ListrikKu menghitung estimasi tagihan
pascabayar termasuk rekening minimum (40 jam nyala) dan PPJ opsional.

## Pemasangan

Butuh Python 3.10 ke atas. Tanpa dependensi tambahan.

```bash
pip install .
listrikku --version
```

Atau langsung tanpa instalasi:

```bash
python -m listrikku --help
```

## Pemakaian

Atur daya terpasang rumahmu dulu (sekali saja):

```bash
listrikku daya atur 1300
```

Catat bacaan meteran — cukup tanggal dan angka kWh yang tampil di meteran:

```bash
listrikku meter tambah --tanggal 2026-11-01 --kwh 1234.5
listrikku meter tambah --tanggal 2026-11-12 --kwh 1280.0
```

Lihat riwayat bacaan dan pemakaian:

```bash
listrikku meter daftar
listrikku pakai
```

Perkirakan tagihan bulan berjalan (pascabayar; tambah `--ppj 3` bila
daerahmu memungut PPJ 3%):

```bash
listrikku tagihan
listrikku tagihan --ppj 3
```

Cara menghitungnya: rata-rata harian dari bacaan bulan ini dikali
jumlah hari sebulan. Bila belum ada bacaan bulan ini, dipakai rata-rata
periode terakhir — dan itu ditulis jelas di hasil, bukan disembunyikan.
Tagihan memakai rekening minimum 40 jam nyala × daya terpasang: bila
proyeksi pemakaianmu di bawah itu, yang ditagih adalah rekening
minimumnya. Ingat, ini perkiraan — tagihan resmi PLN bisa berbeda.

Daya tersimpan di `listrikku.json`, jadi cukup diatur sekali:

```bash
listrikku daya atur 1300
listrikku daya atur 900 --rtm   # golongan 900 VA RTM (tanpa subsidi)
listrikku daya lihat
```

Laporan bulanan + peringatan bila pemakaian melonjak dari rata-rata:

```bash
listrikku laporan --bulan 2026-11
```

Laporan menampilkan total kWh bulan itu, rata-rata harian, dan
perbandingan dengan bulan sebelumnya bila ada datanya. Bila rata-rata
harian bulan ini naik lebih dari 20% dari bulan lalu, ListrikKu memberi
peringatan "pemakaian melonjak" — tanda untuk memeriksa alat elektronik
di rumah. Perintah `pakai` menampilkan tabel yang sama antar bacaan:
tanggal, jumlah hari, kWh terpakai, dan rata-rata harian tiap periode.

## Token prabayar

Buat yang pakai meteran prabayar (token), ListrikKu menghitung berapa
kWh yang didapat dari nominal rupiah — setelah dipotong PPJ — lalu
memperkirakan sisa token dan kapan habisnya.

Beli token (nominal minimal Rp20.000, sesuai denominasi PLN):

```bash
listrikku token beli --nominal 100000 --ppj 3 --tanggal 2026-11-01
```

```
Token 2026-11-01: Rp100.000 -> 67,2 kWh
Daya terpasang : 1.300 VA (R-1/TR) — Rp1.444,70/kWh
PPJ 3% dipotong: nilai token Rp97.087
Pembelian tercatat — cek perkiraan sisanya dengan 'token sisa'.
```

Cara menghitungnya: Rp100.000 / 1,03 = Rp97.087 bersih, dibagi tarif
Rp1.444,70 = 67,2 kWh. Biaya admin loket/agen tidak dihitung — yang
dihitung hanya nilai tokennya.

Cek sisa token + perkiraan hari tersisa:

```bash
listrikku token sisa
```

```
Token terakhir: 2026-11-01 — Rp100.000 (67,2 kWh)
Terpakai sejak beli: 36,0 kWh
Sisa token        : 31,2 kWh
Rata-rata harian  : 3,3 kWh/hari (periode terakhir)
Perkiraan habis   : 10 hari lagi (sekitar 2026-11-22)
Perkiraan dari rata-rata harianmu — pemakaian sebenarnya bisa berbeda.
```

Sisa dihitung dari kWh token terakhir dikurangi pemakaian sejak tanggal
beli (periode antar bacaan dibagi proporsional per hari, jadi tanggal
beli yang jatuh di tengah periode tetap terhitung adil). Bila sisa
tinggal 3 hari atau kurang, muncul peringatan "Token hampir habis".

Pengingat isi ulang — tampilkan peringatan bila token diperkirakan
habis dalam N hari (bawaan 3 hari):

```bash
listrikku token ingatkan
listrikku token ingatkan --ambang 12
```

```
Token terakhir: 2026-11-01 — Rp100.000 (67,2 kWh)
Sisa token        : 31,2 kWh
Perkiraan habis   : 10 hari lagi (sekitar 2026-11-22)
⚠ Token hampir habis — tersisa 10 hari (ambang 12 hari). Segera isi ulang sebelum gelap.
```

## Ekspor CSV

Ekspor data ke CSV — tampil di layar, atau tulis ke file dengan
`--keluar`. Tiga jenis ekspor:

```bash
listrikku ekspor --jenis bacaan
listrikku ekspor --jenis laporan --bulan 2026-11
listrikku ekspor --jenis token
listrikku ekspor --jenis laporan --bulan 2026-11 --keluar laporan-nov.csv
```

Contoh nyata dari data contoh (riwayat bacaan):

```csv
tanggal,meter_kwh,catatan
2026-10-01,1000.0,
2026-10-15,1050.0,
2026-11-01,1104.0,
2026-11-12,1140.0,
```

Contoh laporan November 2026 (periode dibagi proporsional per hari,
plus baris TOTAL):

```csv
tanggal_dari,tanggal_sampai,hari,pakai_kwh,rata_harian_kwh
2026-11-01,2026-11-12,11,36.000,3.273
TOTAL,2026-11,11,36.000,3.273
```

Contoh pembelian token (data contoh + satu pembelian Rp100.000
pada 1 Nov 2026, PPJ 3%):

```csv
tanggal,nominal_rp,token_kwh
2026-11-01,100000,67.202
```

Format CSV memakai koma sebagai pemisah dan desimal dengan titik,
supaya langsung bisa dibuka di spreadsheet.

## Daftar perintah

| Perintah | Fungsi |
| --- | --- |
| `listrikku daya atur <VA> [--rtm]` | Atur daya terpasang (sekali saja) |
| `listrikku daya lihat` | Lihat daya terpasang + tarif |
| `listrikku meter tambah --tanggal T --kwh N` | Catat satu bacaan meteran |
| `listrikku meter daftar` | Tampilkan semua bacaan |
| `listrikku meter hapus <nomor>` | Hapus satu bacaan |
| `listrikku pakai` | Tabel pemakaian antar bacaan |
| `listrikku laporan --bulan YYYY-MM` | Laporan bulanan + perbandingan |
| `listrikku tagihan [--ppj N]` | Perkiraan tagihan pascabayar |
| `listrikku token beli --nominal N [--ppj N]` | Beli token, hitung kWh-nya |
| `listrikku token sisa` | Sisa token + perkiraan hari tersisa |
| `listrikku token ingatkan [--ambang N]` | Pengingat isi ulang token |
| `listrikku ekspor --jenis bacaan\|laporan\|token` | Ekspor data ke CSV |
| `listrikku --version` | Tampilkan versi |

Semua perintah menerima `--data berkas.json` untuk memakai file data
lain (bawaan: `listrikku.json` di folder berjalan, atau `$LISTRIKKU_DATA`).

## Mencoba dengan data contoh

Repo ini menyertakan data contoh dua bulan (`contoh/listrikku-contoh.json`):
rumah 1.300 VA dengan bacaan 1 Okt 2026 (1.000 kWh), 15 Okt (1.050 kWh),
1 Nov (1.104 kWh), dan 12 Nov (1.140 kWh).

```bash
listrikku --data contoh/listrikku-contoh.json pakai
listrikku --data contoh/listrikku-contoh.json laporan --bulan 2026-11
listrikku --data contoh/listrikku-contoh.json tagihan
listrikku --data contoh/listrikku-contoh.json ekspor --jenis bacaan
listrikku --data contoh/listrikku-contoh.json ekspor --jenis laporan --bulan 2026-11
```

Untuk mencoba token, salin dulu datanya (supaya data contoh tetap
murni), lalu beli token dan cek sisanya:

```bash
cp contoh/listrikku-contoh.json coba.json
listrikku --data coba.json token beli --nominal 100000 --ppj 3 --tanggal 2026-11-01
listrikku --data coba.json token sisa
listrikku --data coba.json token ingatkan --ambang 12
listrikku --data coba.json ekspor --jenis token
```

Angka yang keluar sudah diverifikasi cocok dengan hitungan tangan:

- Pemakaian: 50 kWh / 14 hari, lalu 54 kWh / 17 hari, lalu 36 kWh / 11 hari
  (total 140 kWh dalam 42 hari).
- Oktober 2026: 100,8 kWh (30 hari tercakup, rata-rata 3,4 kWh/hari) —
  50 kWh penuh dari periode pertama + 54 × 16/17 hari dari periode kedua.
- November 2026: 36,0 kWh (11 hari tercakup, rata-rata 3,3 kWh/hari) —
  turun 3% dari Oktober, jadi tanpa peringatan lonjakan.
- Perkiraan tagihan November: rata-rata 3,273 kWh/hari × 30 hari =
  98,2 kWh × Rp1.444,70 = Rp141.855 (di atas rekening minimum 52 kWh);
  dengan PPJ 3% menjadi Rp146.111.
- Token: Rp100.000 PPJ 3% → 67,2 kWh; terpakai sejak 1 Nov 36,0 kWh
  → sisa 31,2 kWh, habis sekitar 10 hari lagi (22 Nov 2026).
- Ekspor CSV: bacaan 4 baris; laporan November 36,000 kWh / 11 hari
  + baris TOTAL; token 1 baris (100000 → 67.202 kWh).

## Menjalankan test

Tanpa dependensi tambahan (unittest bawaan Python):

```bash
python -m unittest discover -s tests
```

Test mencakup model (tambah/daftar/hapus, tanggal duplikat, angka turun,
hitung pemakaian), tarif (semua golongan, rekening minimum, PPJ),
laporan, token (hitung kWh semua golongan, PPJ, sisa + hari tersisa,
pengingat), ekspor CSV (tiga jenis, header + isi, tulis ke file), dan
CLI end-to-end (alur catat → pakai → tagihan → laporan → token →
ekspor; input salah keluar dengan kode 1 dan pesan yang ramah).

## Format data

Satu file JSON, mudah dibaca dan dicadangkan manual:

```json
{
  "daya": 1300,
  "bacaan": [
    {"tanggal": "2026-11-01", "kwh": 1234.5},
    {"tanggal": "2026-11-12", "kwh": 1280.0}
  ],
  "token": [
    {"tanggal": "2026-11-01", "nominal": 100000, "kwh": 67.202}
  ]
}
```

## Rencana

- Pengingat jadwal catat meteran
- Mode interaktif / antarmuka web kecil

## Lisensi

MIT — lihat [LICENSE](LICENSE).
