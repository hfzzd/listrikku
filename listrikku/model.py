"""Model data ListrikKu: bacaan meteran dan pemakaian antar bacaan.

Semua data disimpan dalam satu file JSON agar mudah dibaca, dicadangkan,
dan diperiksa manual oleh pengguna:

    {
      "daya": 1300,
      "rtm": false,
      "bacaan": [
        {"tanggal": "2026-11-01", "kwh": 1234.5},
        {"tanggal": "2026-11-12", "kwh": 1280.0}
      ]
    }

`daya` (VA) diisi lewat perintah `daya atur` — dipakai nanti untuk
estimasi tagihan. `rtm` menandai golongan 900 VA RTM (tanpa subsidi).
`bacaan` selalu disimpan terurut berdasarkan tanggal;
angka kWh meteran hanya bisa naik (tidak pernah turun).
"""

import calendar
import json
import os
from datetime import date, datetime

DEFAULT_DATA_FILE = "listrikku.json"


class ListrikKuError(ValueError):
    """Kesalahan input dari pengguna (tanggal salah, kWh turun, dst.)."""


def data_kosong():
    """Struktur data awal yang masih kosong."""
    return {"daya": None, "rtm": False, "bacaan": [], "token": []}


def muat(path):
    """Muat data dari file JSON; kembalikan data kosong bila file belum ada."""
    if not os.path.exists(path):
        return data_kosong()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("daya", None)
    data.setdefault("rtm", False)
    data.setdefault("bacaan", [])
    data.setdefault("token", [])
    return data


def simpan(path, data):
    """Simpan data ke file JSON (ditulis atomik lewat file sementara)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def _tanggal_valid(tanggal):
    """Pastikan tanggal berformat YYYY-MM-DD yang benar-benar ada."""
    try:
        datetime.strptime(tanggal, "%Y-%m-%d")
    except (ValueError, TypeError):
        raise ListrikKuError(
            f"Tanggal '{tanggal}' tidak valid (pakai format YYYY-MM-DD).")
    return tanggal


def tambah_bacaan(data, tanggal, kwh, catatan=None):
    """Catat satu bacaan meteran.

    Satu tanggal hanya boleh punya satu bacaan. Angka kWh tidak boleh
    lebih kecil dari bacaan pada tanggal sebelumnya dan tidak boleh lebih
    besar dari bacaan pada tanggal sesudahnya — meteran hanya bergerak
    maju, jadi angka yang melanggar itu pasti salah catat.
    """
    tanggal = _tanggal_valid(tanggal) if tanggal else date.today().isoformat()
    try:
        kwh = float(kwh)
    except (TypeError, ValueError):
        raise ListrikKuError(f"Angka meteran '{kwh}' tidak valid.")
    if kwh < 0:
        raise ListrikKuError("Angka meteran tidak boleh negatif.")
    bacaan = sorted(data["bacaan"], key=lambda b: b["tanggal"])
    if any(b["tanggal"] == tanggal for b in bacaan):
        raise ListrikKuError(
            f"Tanggal {tanggal} sudah punya bacaan. Hapus dulu yang lama "
            "dengan 'meter hapus' bila memang salah catat.")
    sebelum = [b for b in bacaan if b["tanggal"] < tanggal]
    sesudah = [b for b in bacaan if b["tanggal"] > tanggal]
    if sebelum and kwh < sebelum[-1]["kwh"]:
        raise ListrikKuError(
            f"Angka {kwh} lebih kecil dari bacaan {sebelum[-1]['tanggal']} "
            f"({sebelum[-1]['kwh']} kWh) — meteran tidak pernah turun.")
    if sesudah and kwh > sesudah[0]["kwh"]:
        raise ListrikKuError(
            f"Angka {kwh} lebih besar dari bacaan {sesudah[0]['tanggal']} "
            f"({sesudah[0]['kwh']} kWh) — cek lagi angka yang diketik.")
    entri = {"tanggal": tanggal, "kwh": kwh}
    if catatan:
        entri["catatan"] = catatan.strip()
    data["bacaan"].append(entri)
    data["bacaan"].sort(key=lambda b: b["tanggal"])
    return entri


def daftar_bacaan(data):
    """Kembalikan semua bacaan terurut berdasarkan tanggal."""
    return sorted(data["bacaan"], key=lambda b: b["tanggal"])


def hapus_bacaan(data, nomor):
    """Hapus bacaan berdasarkan nomor urut (1-based, sesuai `meter daftar`).

    Mengembalikan bacaan yang dihapus.
    """
    bacaan = daftar_bacaan(data)
    if nomor < 1 or nomor > len(bacaan):
        raise ListrikKuError(
            f"Tidak ada bacaan nomor {nomor} "
            f"(ada {len(bacaan)} bacaan).")
    target = bacaan[nomor - 1]
    data["bacaan"].remove(target)
    return target


def hitung_pemakaian(data):
    """Hitung pemakaian antar bacaan yang berurutan.

    Mengembalikan daftar periode, masing-masing berisi tanggal awal dan
    akhir, jumlah hari, kWh terpakai, dan rata-rata kWh per hari.
    Butuh minimal dua bacaan; bila kurang, kembalikan daftar kosong.
    """
    bacaan = daftar_bacaan(data)
    periode = []
    for awal, akhir in zip(bacaan, bacaan[1:]):
        t_awal = datetime.strptime(awal["tanggal"], "%Y-%m-%d").date()
        t_akhir = datetime.strptime(akhir["tanggal"], "%Y-%m-%d").date()
        hari = (t_akhir - t_awal).days
        if hari <= 0:
            continue
        kwh = round(akhir["kwh"] - awal["kwh"], 3)
        periode.append({
            "dari": awal["tanggal"],
            "sampai": akhir["tanggal"],
            "hari": hari,
            "kwh": kwh,
            "rata_harian": round(kwh / hari, 3),
        })
    return periode


def pemakaian_bulan(data, tahun, bulan):
    """Pemakaian listrik dalam satu bulan kalender.

    Setiap periode antar bacaan dibagi ke bulan-bulan yang dilewatinya
    secara proporsional per hari. Mengembalikan total kWh, jumlah hari
    yang tercakup data dalam bulan itu, dan rata-rata kWh per hari
    (total dibagi hari tercakup — bukan dibagi jumlah hari sebulan,
    supaya bulan yang bacaannya belum lengkap tidak terlihat kecil).
    """
    awal_bulan = date(tahun, bulan, 1)
    akhir_bulan = date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])
    total_kwh = 0.0
    hari_tercakup = 0
    for p in hitung_pemakaian(data):
        t_awal = datetime.strptime(p["dari"], "%Y-%m-%d").date()
        t_akhir = datetime.strptime(p["sampai"], "%Y-%m-%d").date()
        awal = max(t_awal, awal_bulan)
        akhir = min(t_akhir, akhir_bulan)
        tumpang = (akhir - awal).days
        if tumpang <= 0:
            continue
        total_kwh += p["kwh"] * tumpang / p["hari"]
        hari_tercakup += tumpang
    rata = round(total_kwh / hari_tercakup, 3) if hari_tercakup else 0.0
    return {
        "tahun": tahun,
        "bulan": bulan,
        "kwh": round(total_kwh, 3),
        "hari_tercakup": hari_tercakup,
        "rata_harian": rata,
    }
