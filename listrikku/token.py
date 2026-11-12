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
