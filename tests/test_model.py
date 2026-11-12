"""Unit test model ListrikKu (bacaan meteran + pemakaian).

Angka harapan dihitung tangan dari data contoh
(contoh/listrikku-contoh.json) — lihat komentar di tiap test.
"""

import json
import os
import unittest

from listrikku import model

CONTOH = os.path.join(os.path.dirname(__file__), "..", "contoh",
                      "listrikku-contoh.json")


def data_contoh():
    with open(CONTOH, encoding="utf-8") as f:
        return json.load(f)


def data_kosong_dengan(*bacaan):
    data = model.data_kosong()
    for tanggal, kwh in bacaan:
        model.tambah_bacaan(data, tanggal, kwh)
    return data


class TestTambahBacaan(unittest.TestCase):
    def test_tambah_lalu_daftar_terurut(self):
        data = data_kosong_dengan(("2026-11-12", 1280.0),
                                  ("2026-11-01", 1234.5))
        daftar = model.daftar_bacaan(data)
        self.assertEqual([b["tanggal"] for b in daftar],
                         ["2026-11-01", "2026-11-12"])
        self.assertEqual(daftar[0]["kwh"], 1234.5)

    def test_tanggal_duplikat_ditolak(self):
        data = data_kosong_dengan(("2026-11-01", 1234.5))
        with self.assertRaises(model.ListrikKuError):
            model.tambah_bacaan(data, "2026-11-01", 1250.0)
        self.assertEqual(len(data["bacaan"]), 1)

    def test_angka_turun_ditolak(self):
        data = data_kosong_dengan(("2026-11-01", 1234.5))
        with self.assertRaises(model.ListrikKuError):
            model.tambah_bacaan(data, "2026-11-12", 1200.0)
        self.assertEqual(len(data["bacaan"]), 1)

    def test_angka_lebih_besar_dari_bacaan_sesudahnya_ditolak(self):
        data = data_kosong_dengan(("2026-11-01", 1234.5),
                                  ("2026-11-12", 1280.0))
        with self.assertRaises(model.ListrikKuError):
            model.tambah_bacaan(data, "2026-11-05", 1300.0)

    def test_tanggal_tidak_valid_ditolak(self):
        data = model.data_kosong()
        for salah in ("2026-13-01", "01-11-2026", "2026-02-30", "kemarin"):
            with self.assertRaises(model.ListrikKuError, msg=salah):
                model.tambah_bacaan(data, salah, 100.0)

    def test_angka_negatif_dan_bukan_angka_ditolak(self):
        data = model.data_kosong()
        with self.assertRaises(model.ListrikKuError):
            model.tambah_bacaan(data, "2026-11-01", -5)
        with self.assertRaises(model.ListrikKuError):
            model.tambah_bacaan(data, "2026-11-01", "abc")


class TestHapusBacaan(unittest.TestCase):
    def test_hapus_mengembalikan_yang_dihapus(self):
        data = data_kosong_dengan(("2026-11-01", 1234.5),
                                  ("2026-11-12", 1280.0))
        hapus = model.hapus_bacaan(data, 1)
        self.assertEqual(hapus["tanggal"], "2026-11-01")
        self.assertEqual(len(data["bacaan"]), 1)

    def test_hapus_nomor_tidak_ada_ditolak(self):
        data = data_kosong_dengan(("2026-11-01", 1234.5))
        for nomor in (0, 2, -1):
            with self.assertRaises(model.ListrikKuError, msg=str(nomor)):
                model.hapus_bacaan(data, nomor)


class TestHitungPemakaian(unittest.TestCase):
    def test_kurang_dari_dua_bacaan_kosong(self):
        self.assertEqual(model.hitung_pemakaian(model.data_kosong()), [])
        data = data_kosong_dengan(("2026-11-01", 1234.5))
        self.assertEqual(model.hitung_pemakaian(data), [])

    def test_periode_data_contoh_cocok_hitungan_tangan(self):
        # 1000 -> 1050 = 50 kWh / 14 hari (rata 3,571)
        # 1050 -> 1104 = 54 kWh / 17 hari (rata 3,176)
        # 1104 -> 1140 = 36 kWh / 11 hari (rata 3,273)
        periode = model.hitung_pemakaian(data_contoh())
        self.assertEqual(len(periode), 3)
        self.assertEqual(periode[0]["kwh"], 50.0)
        self.assertEqual(periode[0]["hari"], 14)
        self.assertEqual(periode[0]["rata_harian"], 3.571)
        self.assertEqual(periode[1]["kwh"], 54.0)
        self.assertEqual(periode[1]["hari"], 17)
        self.assertEqual(periode[1]["rata_harian"], 3.176)
        self.assertEqual(periode[2]["kwh"], 36.0)
        self.assertEqual(periode[2]["hari"], 11)
        self.assertEqual(periode[2]["rata_harian"], 3.273)


class TestPemakaianBulan(unittest.TestCase):
    def test_oktober_data_contoh(self):
        # 50 kWh penuh (1-15 Okt) + 54 x 16/17 hari (15-31 Okt) = 100,824
        # 30 hari tercakup, rata 100,824 / 30 = 3,361
        hasil = model.pemakaian_bulan(data_contoh(), 2026, 10)
        self.assertEqual(hasil["kwh"], 100.824)
        self.assertEqual(hasil["hari_tercakup"], 30)
        self.assertEqual(hasil["rata_harian"], 3.361)

    def test_november_data_contoh(self):
        # Periode 1-12 Nov: 36 kWh / 11 hari, rata 3,273
        hasil = model.pemakaian_bulan(data_contoh(), 2026, 11)
        self.assertEqual(hasil["kwh"], 36.0)
        self.assertEqual(hasil["hari_tercakup"], 11)
        self.assertEqual(hasil["rata_harian"], 3.273)

    def test_bulan_tanpa_data_nol(self):
        hasil = model.pemakaian_bulan(data_contoh(), 2026, 9)
        self.assertEqual(hasil["kwh"], 0.0)
        self.assertEqual(hasil["hari_tercakup"], 0)
        self.assertEqual(hasil["rata_harian"], 0.0)


class TestMuatSimpan(unittest.TestCase):
    def test_muat_file_tidak_ada_kosong(self):
        data = model.muat("/tmp/listrikku-tidak-ada-xyz.json")
        self.assertEqual(data, {"daya": None, "rtm": False, "bacaan": [],
                                "token": []})

    def test_simpan_lalu_muat_sama(self):
        import tempfile
        data = data_kosong_dengan(("2026-11-01", 1234.5))
        data["daya"] = 1300
        with tempfile.NamedTemporaryFile(suffix=".json",
                                         delete=False) as f:
            path = f.name
        try:
            model.simpan(path, data)
            self.assertEqual(model.muat(path), data)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
