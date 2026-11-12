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
