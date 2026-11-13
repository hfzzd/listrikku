"""Token listrik prabayar PLN: beli token + perkiraan sisa token.

Token prabayar: nominal yang dibayar dipotong PPJ (pajak penerangan
jalan) dulu, sisanya dibagi tarif per kWh. Denominasi token PLN mulai
Rp20.000. Biaya admin loket/agen tidak dihitung di sini — yang
dihitung hanya nilai tokennya.
"""

from datetime import date, datetime, timedelta

from . import model, tarif

NOMINAL_MIN = 20000


def token_kwh(nominal, daya, rtm=False, ppj=0.0):
    """Hitung kWh yang didapat dari pembelian token senilai `nominal`.

    Mengembalikan rincian: golongan, tarif, nominal bersih setelah PPJ,
    dan kWh token.
    """
    try:
        nominal = float(nominal)
    except (TypeError, ValueError):
        raise model.ListrikKuError(f"Nominal '{nominal}' tidak valid.")
    if nominal < NOMINAL_MIN:
        raise model.ListrikKuError(
            f"Nominal token minimal Rp{NOMINAL_MIN:,} — denominasi "
            "token PLN mulai Rp20.000.")
    try:
        ppj = float(ppj)
    except (TypeError, ValueError):
        raise model.ListrikKuError(f"PPJ '{ppj}' tidak valid.")
    if ppj < 0:
        raise model.ListrikKuError("PPJ tidak boleh negatif.")
    golongan, tarif_kwh = tarif.golongan_dan_tarif(daya, rtm)
    bersih = nominal / (1 + ppj / 100)
    return {
        "golongan": golongan,
        "tarif": tarif_kwh,
        "nominal": round(nominal, 2),
        "ppj_persen": ppj,
        "bersih": round(bersih, 2),
        "kwh": round(bersih / tarif_kwh, 3),
    }


def pemakaian_sejak(data, tanggal):
    """Pemakaian (kWh) sejak `tanggal` sampai bacaan terakhir.

    Periode antar bacaan dibagi proporsional per hari, supaya tanggal
    beli yang jatuh di tengah periode tetap terhitung adil.
    """
    t_beli = datetime.strptime(tanggal, "%Y-%m-%d").date()
    bacaan = model.daftar_bacaan(data)
    if not bacaan:
        return 0.0
    t_akhir = datetime.strptime(bacaan[-1]["tanggal"], "%Y-%m-%d").date()
    total = 0.0
    for p in model.hitung_pemakaian(data):
        t_awal = datetime.strptime(p["dari"], "%Y-%m-%d").date()
        t_sampai = datetime.strptime(p["sampai"], "%Y-%m-%d").date()
        awal = max(t_awal, t_beli)
        akhir = min(t_sampai, t_akhir)
        tumpang = (akhir - awal).days
        if tumpang <= 0:
            continue
        total += p["kwh"] * tumpang / p["hari"]
    return round(total, 3)


def sisa_token(data, tanggal_acuan=None):
    """Perkiraan sisa token dari pembelian terakhir.

    Sisa kWh = kWh token terakhir − pemakaian sejak tanggal beli.
    Hari tersisa dihitung dari rata-rata harian periode terakhir.
    Mengembalikan rincian lengkap untuk ditampilkan.
    """
    pembelian = sorted(data.get("token", []), key=lambda t: t["tanggal"])
    if not pembelian:
        raise model.ListrikKuError(
            "Belum ada pembelian token yang tercatat. Beli dulu dengan "
            "'token beli --nominal 100000'.")
    terakhir = pembelian[-1]
    periode = model.hitung_pemakaian(data)
    if not periode:
        raise model.ListrikKuError(
            "Belum cukup data untuk memperkirakan sisa token — catat "
            "minimal 2 bacaan meteran dulu dengan 'meter tambah'.")
    dipakai = pemakaian_sejak(data, terakhir["tanggal"])
    sisa = round(max(0.0, terakhir["kwh"] - dipakai), 3)
    rata_harian = periode[-1]["rata_harian"]
    hari_ini = tanggal_acuan or date.today()
    if rata_harian > 0:
        hari_tersisa = round(sisa / rata_harian, 1)
        tanggal_habis = hari_ini + timedelta(days=int(sisa / rata_harian))
    else:
        hari_tersisa = None
        tanggal_habis = None
    return {
        "pembelian": terakhir,
        "dipakai_kwh": dipakai,
        "sisa_kwh": sisa,
        "rata_harian": rata_harian,
        "hari_tersisa": hari_tersisa,
        "tanggal_habis": tanggal_habis.isoformat() if tanggal_habis else None,
        "tanggal_acuan": hari_ini.isoformat(),
    }


def beli_token(data, nominal, ppj=0.0, tanggal=None):
    """Beli token: hitung kWh-nya lalu simpan pembelian ke data.

    Mengembalikan (entri pembelian, rincian token_kwh).
    """
    if not data["daya"]:
        raise model.ListrikKuError(
            "Daya belum diatur — token tidak bisa dihitung tanpa tarif. "
            "Atur dulu dengan 'daya atur <VA>', misal: "
            "listrikku daya atur 1300")
    tanggal = tanggal or date.today().isoformat()
    try:
        datetime.strptime(tanggal, "%Y-%m-%d")
    except (ValueError, TypeError):
        raise model.ListrikKuError(
            f"Tanggal '{tanggal}' tidak valid (pakai format YYYY-MM-DD).")
    hasil = token_kwh(nominal, data["daya"], data["rtm"], ppj)
    entri = {
        "tanggal": tanggal,
        "nominal": hasil["nominal"],
        "kwh": hasil["kwh"],
    }
    data.setdefault("token", []).append(entri)
    data["token"].sort(key=lambda t: t["tanggal"])
    return entri, hasil
