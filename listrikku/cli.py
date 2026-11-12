"""Antarmuka baris perintah (CLI) ListrikKu.

Contoh pemakaian:
    listrikku meter tambah --tanggal 2026-11-01 --kwh 1234.5
    listrikku meter daftar
    listrikku meter hapus 2
"""

import argparse
import os
import sys

from . import __version__, model


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

    return p


def _format_kwh(kwh):
    """Tampilkan kWh dengan pemisah ribuan ala Indonesia."""
    return f"{kwh:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


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


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.perintah == "meter" and args.aksi == "tambah":
            _cmd_meter_tambah(args)
        elif args.perintah == "meter" and args.aksi == "daftar":
            _cmd_meter_daftar(args)
        elif args.perintah == "meter" and args.aksi == "hapus":
            _cmd_meter_hapus(args)
    except model.ListrikKuError as e:
        print(f"listrikku: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
