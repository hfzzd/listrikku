"""Unit test ekspor CSV ListrikKu (bacaan, laporan bulanan, token)."""

import csv
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from listrikku import cli, export, model, token

CONTOH = os.path.join(os.path.dirname(__file__), "..", "contoh",
                      "listrikku-contoh.json")


def data_contoh():
    with open(CONTOH, encoding="utf-8") as f:
        return json.load(f)


def baca_csv(teks):
    """Urai teks CSV jadi daftar baris (list of list of str)."""
    return list(csv.reader(io.StringIO(teks)))


class TestEksporBacaan(unittest.TestCase):
    def test_header_dan_isi_benar(self):
        baris = baca_csv(export.bacaan_csv(data_contoh()))
        self.assertEqual(baris[0], ["tanggal", "meter_kwh", "catatan"])
        self.assertEqual(baris[1:], [
            ["2026-10-01", "1000.0", ""],
            ["2026-10-15", "1050.0", ""],
            ["2026-11-01", "1104.0", ""],
            ["2026-11-12", "1140.0", ""],
        ])

    def test_catatan_ikut_terekspor(self):
        data = model.data_kosong()
        model.tambah_bacaan(data, "2026-11-01", 1000.0, "awal bulan")
        baris = baca_csv(export.bacaan_csv(data))
        self.assertEqual(baris[1], ["2026-11-01", "1000.0", "awal bulan"])

    def test_tanpa_bacaan_hanya_header(self):
        baris = baca_csv(export.bacaan_csv(model.data_kosong()))
        self.assertEqual(baris, [["tanggal", "meter_kwh", "catatan"]])


class TestEksporLaporan(unittest.TestCase):
    def test_laporan_sebulan_penuh(self):
        # November 2026: satu periode penuh 1-12 Nov (36 kWh / 11 hari).
        baris = baca_csv(export.laporan_csv(data_contoh(), 2026, 11))
        self.assertEqual(baris[0], ["tanggal_dari", "tanggal_sampai", "hari",
                                    "pakai_kwh", "rata_harian_kwh"])
        self.assertEqual(baris[1], ["2026-11-01", "2026-11-12", "11",
                                    "36.000", "3.273"])
        self.assertEqual(baris[2], ["TOTAL", "2026-11", "11",
                                    "36.000", "3.273"])

    def test_laporan_terpotong_proporsional_per_bulan(self):
        # Oktober 2026 — hitungan tangan:
        # 1-15 Okt: 50 kWh / 14 hari penuh.
        # 15 Okt-1 Nov: 54 kWh / 17 hari; yang jatuh di Oktober 16 hari
        # (15-31 Okt) -> 54 x 16/17 = 50,824 kWh.
        # TOTAL: 100,824 kWh / 30 hari = 3,361 kWh/hari.
        baris = baca_csv(export.laporan_csv(data_contoh(), 2026, 10))
        self.assertEqual(baris[1], ["2026-10-01", "2026-10-15", "14",
                                    "50.000", "3.571"])
        self.assertEqual(baris[2], ["2026-10-15", "2026-11-01", "16",
                                    "50.824", "3.176"])
        self.assertEqual(baris[3], ["TOTAL", "2026-10", "30",
                                    "100.824", "3.361"])

    def test_bulan_tanpa_data_total_nol(self):
        baris = baca_csv(export.laporan_csv(data_contoh(), 2026, 9))
        self.assertEqual(baris[1:], [["TOTAL", "2026-09", "0",
                                      "0.000", "0.000"]])


class TestEksporToken(unittest.TestCase):
    def test_header_dan_isi_benar(self):
        data = data_contoh()
        token.beli_token(data, 100000, tanggal="2026-11-01")
        token.beli_token(data, 50000, tanggal="2026-11-05")
        baris = baca_csv(export.token_csv(data))
        self.assertEqual(baris[0], ["tanggal", "nominal_rp", "token_kwh"])
        self.assertEqual(baris[1], ["2026-11-01", "100000", "69.219"])
        self.assertEqual(baris[2], ["2026-11-05", "50000", "34.609"])

    def test_tanpa_pembelian_hanya_header(self):
        baris = baca_csv(export.token_csv(model.data_kosong()))
        self.assertEqual(baris, [["tanggal", "nominal_rp", "token_kwh"]])


class TestEksporCliKeluar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data = os.path.join(self.tmp, "data.json")
        model.simpan(self.data, data_contoh())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _jalankan(self, *args):
        keluar = io.StringIO()
        galat = io.StringIO()
        with redirect_stdout(keluar), redirect_stderr(galat):
            kode = cli.main(list(args))
        return kode, keluar.getvalue(), galat.getvalue()

    def test_keluar_menulis_file_bacaan(self):
        target = os.path.join(self.tmp, "bacaan.csv")
        kode, out, _ = self._jalankan(
            "--data", self.data, "ekspor", "--jenis", "bacaan",
            "--keluar", target)
        self.assertEqual(kode, 0)
        self.assertIn("Diekspor ke", out)
        with open(target, encoding="utf-8") as f:
            baris = baca_csv(f.read())
        self.assertEqual(baris[0], ["tanggal", "meter_kwh", "catatan"])
        self.assertEqual(len(baris), 5)  # header + 4 bacaan

    def test_keluar_menulis_file_laporan(self):
        target = os.path.join(self.tmp, "laporan.csv")
        kode, _, _ = self._jalankan(
            "--data", self.data, "ekspor", "--jenis", "laporan",
            "--bulan", "2026-11", "--keluar", target)
        self.assertEqual(kode, 0)
        with open(target, encoding="utf-8") as f:
            baris = baca_csv(f.read())
        self.assertEqual(baris[-1], ["TOTAL", "2026-11", "11",
                                     "36.000", "3.273"])

    def test_tanpa_keluar_tampil_di_layar(self):
        kode, out, _ = self._jalankan(
            "--data", self.data, "ekspor", "--jenis", "token")
        self.assertEqual(kode, 0)
        self.assertEqual(baca_csv(out)[0],
                         ["tanggal", "nominal_rp", "token_kwh"])

    def test_laporan_tanpa_bulan_ditolak(self):
        kode, _, galat = self._jalankan(
            "--data", self.data, "ekspor", "--jenis", "laporan")
        self.assertEqual(kode, 1)
        self.assertIn("--bulan", galat)


if __name__ == "__main__":
    unittest.main()
