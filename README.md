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

Salah catat? Hapus berdasarkan nomor di `meter daftar`:

```bash
listrikku meter hapus 2
```

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

## Menjalankan test

Tanpa dependensi tambahan (unittest bawaan Python):

```bash
python -m unittest discover -s tests
```

Test mencakup model (tambah/daftar/hapus, tanggal duplikat, angka turun,
hitung pemakaian), tarif (semua golongan, rekening minimum, PPJ),
laporan, dan CLI end-to-end (alur catat → pakai → tagihan → laporan;
input salah keluar dengan kode 1).

## Format data

Satu file JSON, mudah dibaca dan dicadangkan manual:

```json
{
  "daya": 1300,
  "bacaan": [
    {"tanggal": "2026-11-01", "kwh": 1234.5},
    {"tanggal": "2026-11-12", "kwh": 1280.0}
  ]
}
```

## Rencana

- Perkiraan sisa token & tanggal habis untuk prabayar (token)
- Ekspor CSV riwayat bacaan dan laporan
- Pengingat jadwal catat meteran

## Lisensi

MIT — lihat [LICENSE](LICENSE).
