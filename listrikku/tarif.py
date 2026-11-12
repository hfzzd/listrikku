"""Tarif listrik rumah tangga PLN + estimasi tagihan pascabayar.

Tarif: Triwulan IV 2026 (Oktober–Desember 2026), sesuai Permen ESDM
No. 7 Tahun 2024 — tarif tidak naik dari triwulan sebelumnya.

Rekening minimum pascabayar: 40 jam nyala x daya terpasang (aturan PLN:
biaya minimum yang ditagih walau pemakaian kecil). PPJ (pajak
penerangan jalan) besarnya beda tiap daerah; bawaan 0%.
"""

import calendar
from datetime import date

from . import model

# Daya (VA) -> (golongan, tarif per kWh dalam rupiah).
TARIF = {
    450: ("R-1/TR subsidi", 415),
    900: ("R-1/TR subsidi", 605),
    1300: ("R-1/TR", 1444.70),
    2200: ("R-1/TR", 1444.70),
}

# 900 VA RTM (rumah tangga mampu, tanpa subsidi) punya tarif sendiri.
TARIF_900_RTM = ("R-1/TR (RTM)", 1352)
# 3.500 VA ke atas (R-2/R-3) memakai satu tarif yang sama.
TARIF_BESAR = ("R-2/R-3", 1699.53)

DAYA_BESAR_MIN = 3500
DAYA_BESAR_MAX = 200000  # R-3 sampai 200 kVA.

JAM_NYALA_MINIMUM = 40


def golongan_dan_tarif(daya, rtm=False):
    """Kembalikan (golongan, tarif per kWh) untuk daya terpasang.

    `rtm=True` hanya berlaku untuk 900 VA (golongan RTM tanpa subsidi).
    """
    try:
        daya = int(daya)
    except (TypeError, ValueError):
        raise model.ListrikKuError(f"Daya '{daya}' tidak valid.")
    if daya == 900 and rtm:
        return TARIF_900_RTM
    if daya in TARIF:
        return TARIF[daya]
    if DAYA_BESAR_MIN <= daya <= DAYA_BESAR_MAX:
        return TARIF_BESAR
    raise model.ListrikKuError(
        "Daya tidak dikenal. Daya rumah tangga PLN: 450, 900, 1.300, "
        "2.200 VA, atau 3.500 VA ke atas (sampai 200.000 VA).")


def atur_daya(data, daya, rtm=False):
    """Simpan daya terpasang ke data (validasi dulu via tarif)."""
    if rtm and int(daya) != 900:
        raise model.ListrikKuError(
            "--rtm hanya berlaku untuk daya 900 VA (golongan RTM).")
    golongan_dan_tarif(daya, rtm)  # validasi
    data["daya"] = int(daya)
    data["rtm"] = bool(rtm)
    return data["daya"]


def rekening_minimum_kwh(daya):
    """Rekening minimum: 40 jam nyala x daya terpasang (dalam kWh)."""
    return JAM_NYALA_MINIMUM * daya / 1000


def hitung_tagihan(kwh, daya, rtm=False, ppj=0.0):
    """Hitung tagihan pascabayar dari pemakaian sebulan (kWh).

    Tagihan = max(pemakaian, rekening minimum) x tarif, lalu ditambah
    PPJ bila ada. Mengembalikan rincian angka untuk ditampilkan.
    """
    if kwh < 0:
        raise model.ListrikKuError("Pemakaian tidak boleh negatif.")
    try:
        ppj = float(ppj)
    except (TypeError, ValueError):
        raise model.ListrikKuError(f"PPJ '{ppj}' tidak valid.")
    if ppj < 0:
        raise model.ListrikKuError("PPJ tidak boleh negatif.")
    golongan, tarif = golongan_dan_tarif(daya, rtm)
    minimum = rekening_minimum_kwh(daya)
    ditagih = max(kwh, minimum)
    biaya = round(ditagih * tarif, 2)
    ppj_rp = round(biaya * ppj / 100, 2)
    return {
        "golongan": golongan,
        "tarif": tarif,
        "pemakaian_kwh": round(kwh, 3),
        "minimum_kwh": round(minimum, 3),
        "ditagih_kwh": round(ditagih, 3),
        "di_bawah_minimum": kwh < minimum,
        "biaya": biaya,
        "ppj_persen": ppj,
        "ppj_rp": ppj_rp,
        "total": round(biaya + ppj_rp, 2),
    }


def proyeksi_bulan_berjalan(data, tanggal_acuan=None):
    """Proyeksikan pemakaian bulan berjalan ke sebulan penuh.

    Rata-rata harian diambil dari bacaan bulan ini; bila belum ada
    bacaan bulan ini, dipakai rata-rata periode terakhir — dan itu
    dikatakan dengan jujur di hasil (`sumber`).
    Butuh minimal 2 bacaan; bila kurang, tolak dengan pesan ramah.
    """
    bacaan = model.daftar_bacaan(data)
    if len(bacaan) < 2:
        raise model.ListrikKuError(
            "Belum cukup data untuk memperkirakan tagihan — catat minimal "
            "2 bacaan meteran dulu dengan 'meter tambah'.")
    hari_ini = tanggal_acuan or date.today()
    tahun, bulan = hari_ini.year, hari_ini.month
    hari_bulan = calendar.monthrange(tahun, bulan)[1]
    bulanan = model.pemakaian_bulan(data, tahun, bulan)
    if bulanan["hari_tercakup"] > 0:
        rata_harian = bulanan["rata_harian"]
        sumber = "bulan ini"
    else:
        periode = model.hitung_pemakaian(data)
        rata_harian = periode[-1]["rata_harian"]
        sumber = "periode terakhir"
    return {
        "tahun": tahun,
        "bulan": bulan,
        "hari_bulan": hari_bulan,
        "rata_harian": rata_harian,
        "proyeksi_kwh": round(rata_harian * hari_bulan, 3),
        "sumber": sumber,
    }
