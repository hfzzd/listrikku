"""Antarmuka baris perintah (CLI) ListrikKu.

Contoh pemakaian:
    listrikku meter tambah --tanggal 2026-11-01 --kwh 1234.5
    listrikku meter daftar
    listrikku meter hapus 2
"""

import argparse
import os
import sys

from . import __version__, model, tarif


def _nama_bulan(bulan):
    """Nama bulan Indonesia (1-12)."""
    return ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November",
            "Desember"][bulan]


def _parser():
    p = argparse.ArgumentParser(
        prog="listrikku",
        description="Pencatat meteran listrik + estimasi tagihan PLN.",
    )
    p.add_argument(
        "--data",
        default=os.environ.get("LISTRIKKU_DATA", model.DEFAULT_DATA_FILE),
        help="File data JSON (bawaan: listrikku.json atau $LISTRIKKU_DATA).",
    )
    p.add_argument("--version", action="version",
                   version=f"listrikku {__version__}")
    sub = p.add_subparsers(dest="perintah", required=True)

    meter = sub.add_parser("meter", help="Kelola bacaan meteran.")
    meter_sub = meter.add_subparsers(dest="aksi", required=True)
    m_tambah = meter_sub.add_parser("tambah", help="Catat satu bacaan.")
    m_tambah.add_argument("--tanggal", default=None,
                          help="Tanggal YYYY-MM-DD (bawaan: hari ini).")
    m_tambah.add_argument("--kwh", required=True, type=float,
                          help="Angka kWh yang tampil di meteran.")
    m_tambah.add_argument("--catatan", default=None,
                          help="Catatan singkat (opsional).")
    meter_sub.add_parser("daftar", help="Tampilkan semua bacaan.")
    m_hapus = meter_sub.add_parser("hapus", help="Hapus satu bacaan.")
    m_hapus.add_argument("nomor", type=int,
                         help="Nomor bacaan dari 'meter daftar'.")

    daya = sub.add_parser("daya", help="Atur / lihat daya terpasang.")
    daya_sub = daya.add_subparsers(dest="aksi", required=True)
    d_atur = daya_sub.add_parser("atur", help="Atur daya terpasang (VA).")
    d_atur.add_argument("va", type=int,
                        help="Daya terpasang, misal 450, 900, 1300, 2200.")
    d_atur.add_argument("--rtm", action="store_true",
                        help="Golongan 900 VA RTM (tanpa subsidi).")
    daya_sub.add_parser("lihat", help="Lihat daya terpasang saat ini.")

    tagihan = sub.add_parser(
        "tagihan", help="Perkirakan tagihan bulan berjalan (pascabayar).")
    tagihan.add_argument("--ppj", type=float, default=0.0,
                         help="PPJ daerah dalam persen (bawaan: 0).")

    sub.add_parser("pakai", help="Tampilkan pemakaian antar bacaan.")
    laporan = sub.add_parser(
        "laporan", help="Laporan pemakaian satu bulan + perbandingan.")
    laporan.add_argument("--bulan", required=True,
                         help="Bulan yang dilaporkan, format YYYY-MM.")

    return p


def _format_kwh(kwh):
    """Tampilkan kWh dengan pemisah ribuan ala Indonesia."""
    return f"{kwh:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_rupiah(nilai, desimal=0):
    """Tampilkan rupiah ala Indonesia, misal Rp1.444,70 atau Rp177.798."""
    teks = f"{nilai:,.{desimal}f}"
    return "Rp" + teks.replace(",", "X").replace(".", ",").replace("X", ".")


def _format_daya(daya, rtm=False):
    """Tampilkan daya + golongan + tarif, misal '1.300 VA (R-1/TR)'."""
    golongan, tarif_kwh = tarif.golongan_dan_tarif(daya, rtm)
    va = f"{daya:,}".replace(",", ".")
    return (f"{va} VA ({golongan}) — "
            f"{_format_rupiah(tarif_kwh, desimal=2)}/kWh")


def _cmd_meter_tambah(args):
    data = model.muat(args.data)
    entri = model.tambah_bacaan(data, args.tanggal, args.kwh, args.catatan)
    model.simpan(args.data, data)
    print(f"Bacaan {entri['tanggal']}: {_format_kwh(entri['kwh'])} kWh "
          f"tersimpan di {args.data}.")


def _cmd_meter_daftar(args):
    data = model.muat(args.data)
    bacaan = model.daftar_bacaan(data)
    if not bacaan:
        print("Belum ada bacaan. Catat dulu dengan 'meter tambah'.")
        return
    pemakaian = {(p["sampai"]): p for p in model.hitung_pemakaian(data)}
    print(f"{'No':>3}  {'Tanggal':<10}  {'Meter (kWh)':>12}  {'Pakai sejak lalu':>16}")
    for i, b in enumerate(bacaan, start=1):
        p = pemakaian.get(b["tanggal"])
        pakai = f"{_format_kwh(p['kwh'])} kWh / {p['hari']} hari" if p else "-"
        print(f"{i:>3}  {b['tanggal']:<10}  {_format_kwh(b['kwh']):>12}  {pakai:>16}")


def _cmd_meter_hapus(args):
    data = model.muat(args.data)
    hapus = model.hapus_bacaan(data, args.nomor)
    model.simpan(args.data, data)
    print(f"Bacaan {hapus['tanggal']} ({_format_kwh(hapus['kwh'])} kWh) dihapus.")


def _cmd_daya_atur(args):
    data = model.muat(args.data)
    tarif.atur_daya(data, args.va, args.rtm)
    model.simpan(args.data, data)
    print(f"Daya terpasang diatur ke {_format_daya(data['daya'], data['rtm'])}.")


def _cmd_daya_lihat(args):
    data = model.muat(args.data)
    if not data["daya"]:
        print("Daya belum diatur. Atur dulu dengan 'daya atur <VA>', "
              "misal: listrikku daya atur 1300")
        return
    print(f"Daya terpasang: {_format_daya(data['daya'], data['rtm'])}.")


def _cmd_tagihan(args):
    data = model.muat(args.data)
    if not data["daya"]:
        raise model.ListrikKuError(
            "Daya belum diatur — tagihan tidak bisa dihitung tanpa tarif. "
            "Atur dulu dengan 'daya atur <VA>', misal: "
            "listrikku daya atur 1300")
    proyeksi = tarif.proyeksi_bulan_berjalan(data)
    hasil = tarif.hitung_tagihan(
        proyeksi["proyeksi_kwh"], data["daya"], data["rtm"], args.ppj)
    bulan = _nama_bulan(proyeksi["bulan"])
    print(f"Perkiraan tagihan {bulan} {proyeksi['tahun']} (pascabayar)")
    print(f"Daya terpasang : {_format_daya(data['daya'], data['rtm'])}")
    if proyeksi["sumber"] == "bulan ini":
        print(f"Rata-rata harian: {_format_kwh(proyeksi['rata_harian'])} "
              "kWh/hari (dari bacaan bulan ini)")
    else:
        print(f"Rata-rata harian: {_format_kwh(proyeksi['rata_harian'])} "
              "kWh/hari (belum ada bacaan bulan ini — memakai rata-rata "
              "periode terakhir)")
    print(f"Proyeksi sebulan: {_format_kwh(proyeksi['proyeksi_kwh'])} kWh "
          f"({proyeksi['hari_bulan']} hari)")
    print(f"Rekening minimum: {_format_kwh(hasil['minimum_kwh'])} kWh "
          "(40 jam nyala x daya)")
    if hasil["di_bawah_minimum"]:
        print("Pemakaian di bawah rekening minimum — ditagih sebesar "
              "rekening minimum.")
    print(f"Ditagih         : {_format_kwh(hasil['ditagih_kwh'])} kWh x "
          f"{_format_rupiah(hasil['tarif'], desimal=2)} = "
          f"{_format_rupiah(hasil['biaya'])}")
    if hasil["ppj_persen"]:
        print(f"PPJ {hasil['ppj_persen']:g}%          : "
              f"{_format_rupiah(hasil['ppj_rp'])}")
    print(f"Perkiraan total : {_format_rupiah(hasil['total'])}")
    print("Ini perkiraan dari rata-rata harianmu — tagihan resmi PLN "
          "bisa berbeda.")


def _cmd_pakai(args):
    data = model.muat(args.data)
    periode = model.hitung_pemakaian(data)
    if not periode:
        raise model.ListrikKuError(
            "Belum ada periode pemakaian — catat minimal 2 bacaan dulu "
            "dengan 'meter tambah'.")
    print(f"{'Dari':<10}  {'Sampai':<10}  {'Hari':>4}  "
          f"{'Pakai (kWh)':>12}  {'Rata-rata/hari':>14}")
    total_kwh = 0.0
    total_hari = 0
    for p in periode:
        print(f"{p['dari']:<10}  {p['sampai']:<10}  {p['hari']:>4}  "
              f"{_format_kwh(p['kwh']):>12}  "
              f"{_format_kwh(p['rata_harian']):>14}")
        total_kwh += p["kwh"]
        total_hari += p["hari"]
    print(f"Total: {_format_kwh(total_kwh)} kWh dalam {total_hari} hari "
          f"(rata-rata {_format_kwh(total_kwh / total_hari)} kWh/hari).")


def _cmd_laporan(args):
    data = model.muat(args.data)
    try:
        tahun, bulan = (int(x) for x in args.bulan.split("-"))
        if not (1 <= bulan <= 12) or len(args.bulan) != 7:
            raise ValueError
    except ValueError:
        raise model.ListrikKuError(
            f"Bulan '{args.bulan}' tidak valid "
            "(pakai format YYYY-MM, misal 2026-11).")
    ini = model.pemakaian_bulan(data, tahun, bulan)
    if ini["hari_tercakup"] == 0:
        raise model.ListrikKuError(
            f"Belum ada bacaan untuk {_nama_bulan(bulan)} {tahun} — "
            "catat meteran dulu dengan 'meter tambah'.")
    lalu_tahun, lalu_bulan = ((tahun, bulan - 1) if bulan > 1
                             else (tahun - 1, 12))
    lalu = model.pemakaian_bulan(data, lalu_tahun, lalu_bulan)
    print(f"Laporan pemakaian {_nama_bulan(bulan)} {tahun}")
    print(f"Total pemakaian : {_format_kwh(ini['kwh'])} kWh "
          f"({ini['hari_tercakup']} hari tercakup data)")
    print(f"Rata-rata harian: {_format_kwh(ini['rata_harian'])} kWh/hari")
    if lalu["hari_tercakup"] == 0 or lalu["rata_harian"] == 0:
        print(f"Belum ada data {_nama_bulan(lalu_bulan)} {lalu_tahun} "
              "untuk perbandingan.")
        return
    selisih = ((ini["rata_harian"] - lalu["rata_harian"])
               / lalu["rata_harian"] * 100)
    if selisih > 0:
        arah = f"naik {selisih:.0f}%"
    elif selisih < 0:
        arah = f"turun {abs(selisih):.0f}%"
    else:
        arah = "sama"
    print(f"Bulan lalu ({_nama_bulan(lalu_bulan)} {lalu_tahun}): "
          f"rata-rata {_format_kwh(lalu['rata_harian'])} kWh/hari — {arah}.")
    if selisih > 20:
        print("⚠ Pemakaian melonjak! Rata-rata harian bulan ini naik "
              "lebih dari 20% dari bulan lalu — cek pemakaian alat "
              "elektronik di rumah.")


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.perintah == "meter" and args.aksi == "tambah":
            _cmd_meter_tambah(args)
        elif args.perintah == "meter" and args.aksi == "daftar":
            _cmd_meter_daftar(args)
        elif args.perintah == "meter" and args.aksi == "hapus":
            _cmd_meter_hapus(args)
        elif args.perintah == "daya" and args.aksi == "atur":
            _cmd_daya_atur(args)
        elif args.perintah == "daya" and args.aksi == "lihat":
            _cmd_daya_lihat(args)
        elif args.perintah == "tagihan":
            _cmd_tagihan(args)
        elif args.perintah == "pakai":
            _cmd_pakai(args)
        elif args.perintah == "laporan":
            _cmd_laporan(args)
    except model.ListrikKuError as e:
        print(f"listrikku: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
