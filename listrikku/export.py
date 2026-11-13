"""Ekspor data ListrikKu ke CSV (bacaan meteran, laporan bulanan, token).

Format CSV memakai koma sebagai pemisah dan angka desimal dengan titik,
supaya langsung bisa dibuka di spreadsheet. Nilai yang mengandung koma
atau tanda kutip dikutip sesuai aturan CSV standar.
"""

import csv
import io

from . import model


def _ke_csv(baris):
    """Ubah daftar baris (list of list) menjadi teks CSV."""
    buf = io.StringIO(newline="")
    penulis = csv.writer(buf, lineterminator="\n")
    penulis.writerows(baris)
    return buf.getvalue()


def bacaan_csv(data):
    """CSV semua bacaan meteran: tanggal, meter (kWh), catatan."""
    baris = [["tanggal", "meter_kwh", "catatan"]]
    for b in model.daftar_bacaan(data):
        baris.append([b["tanggal"], f"{b['kwh']:.1f}",
                      b.get("catatan", "")])
    return _ke_csv(baris)


def laporan_csv(data, tahun, bulan):
    """CSV pemakaian satu bulan: satu baris per periode + baris TOTAL.

    Periode yang melewati batas bulan dibagi proporsional per hari,
    sama seperti laporan di layar.
    """
    from datetime import date
    import calendar

    awal_bulan = date(tahun, bulan, 1)
    akhir_bulan = date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])
    baris = [["tanggal_dari", "tanggal_sampai", "hari", "pakai_kwh",
              "rata_harian_kwh"]]
    total_kwh = 0.0
    total_hari = 0
    for p in model.hitung_pemakaian(data):
        t_awal = date.fromisoformat(p["dari"])
        t_akhir = date.fromisoformat(p["sampai"])
        awal = max(t_awal, awal_bulan)
        akhir = min(t_akhir, akhir_bulan)
        tumpang = (akhir - awal).days
        if tumpang <= 0:
            continue
        kwh = round(p["kwh"] * tumpang / p["hari"], 3)
        baris.append([p["dari"], p["sampai"], tumpang, f"{kwh:.3f}",
                      f"{kwh / tumpang:.3f}"])
        total_kwh += kwh
        total_hari += tumpang
    rata = round(total_kwh / total_hari, 3) if total_hari else 0.0
    baris.append(["TOTAL", f"{tahun}-{bulan:02d}", total_hari,
                  f"{total_kwh:.3f}", f"{rata:.3f}"])
    return _ke_csv(baris)


def token_csv(data):
    """CSV semua pembelian token: tanggal, nominal, kWh."""
    baris = [["tanggal", "nominal_rp", "token_kwh"]]
    for t in sorted(data.get("token", []), key=lambda t: t["tanggal"]):
        baris.append([t["tanggal"], f"{t['nominal']:.0f}",
                      f"{t['kwh']:.3f}"])
    return _ke_csv(baris)
