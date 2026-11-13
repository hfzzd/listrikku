"""Unit test CLI ListrikKu end-to-end (alur lengkap + input salah).

Jalankan: python -m unittest discover -s tests
"""

import calendar
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from datetime import date

from listrikku import __version__, cli, model


def jalankan(*args):
    """Jalankan CLI, kembalikan (kode_keluar, stdout, stderr)."""
    keluar = io.StringIO()
    galat = io.StringIO()
    with redirect_stdout(keluar), redirect_stderr(galat):
        kode = cli.main(list(args))
    return kode, keluar.getvalue(), galat.getvalue()


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data = os.path.join(self.tmp, "data.json")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _data(self):
        return ["--data", self.data]

    def _isi_contoh(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "contoh",
                               "listrikku-contoh.json"),
                  encoding="utf-8") as f:
            data = json.load(f)
        model.simpan(self.data, data)


class TestAlurLengkap(CliTestCase):
    def test_catat_pakai_tagihan_laporan(self):
        # Alur: atur daya -> catat 2 bacaan -> pakai -> tagihan -> laporan
        hari_ini = date.today()
        awal_bulan = hari_ini.replace(day=1)
        kode, out, _ = jalankan(*self._data(), "daya", "atur", "1300")
        self.assertEqual(kode, 0)
        self.assertIn("1.300 VA", out)

        kode, out, _ = jalankan(*self._data(), "meter", "tambah",
                                "--tanggal", awal_bulan.isoformat(),
                                "--kwh", "1000")
        self.assertEqual(kode, 0)
        kode, out, _ = jalankan(*self._data(), "meter", "tambah",
                                "--tanggal", hari_ini.isoformat(),
                                "--kwh", "1036")
        self.assertEqual(kode, 0)

        kode, out, _ = jalankan(*self._data(), "meter", "daftar")
        self.assertEqual(kode, 0)
        self.assertIn("36,0", out)

        kode, out, _ = jalankan(*self._data(), "pakai")
        self.assertEqual(kode, 0)
        self.assertIn("36,0", out)
        self.assertIn("Total:", out)

        kode, out, _ = jalankan(*self._data(), "tagihan")
        self.assertEqual(kode, 0)
        self.assertIn("Perkiraan tagihan", out)
        self.assertIn("Perkiraan total", out)

        kode, out, _ = jalankan(*self._data(), "tagihan", "--ppj", "3")
        self.assertEqual(kode, 0)
        self.assertIn("PPJ 3%", out)

        bulan = hari_ini.strftime("%Y-%m")
        kode, out, _ = jalankan(*self._data(), "laporan", "--bulan", bulan)
        self.assertEqual(kode, 0)
        self.assertIn("Laporan pemakaian", out)

    def test_laporan_data_contoh_cocok_hitungan_tangan(self):
        # Nov 2026: 36,0 kWh / 11 hari, rata 3,3; Okt rata 3,4 -> turun 3%
        self._isi_contoh()
        kode, out, _ = jalankan(*self._data(), "laporan", "--bulan",
                                "2026-11")
        self.assertEqual(kode, 0)
        self.assertIn("36,0 kWh (11 hari tercakup data)", out)
        self.assertIn("turun 3%", out)
        self.assertNotIn("melonjak", out)

    def test_laporan_melonjak_lebih_20_persen(self):
        # Okt rata ~0,97 kWh/hari, Nov rata ~10,9 -> naik >1000%, peringatan
        data = model.data_kosong()
        model.tambah_bacaan(data, "2026-10-01", 1000.0)
        model.tambah_bacaan(data, "2026-11-01", 1030.0)
        model.tambah_bacaan(data, "2026-11-12", 1150.0)
        model.simpan(self.data, data)
        kode, out, _ = jalankan(*self._data(), "laporan", "--bulan",
                                "2026-11")
        self.assertEqual(kode, 0)
        self.assertIn("melonjak", out)

    def test_hapus_bacaan_lewat_cli(self):
        self._isi_contoh()
        kode, out, _ = jalankan(*self._data(), "meter", "hapus", "4")
        self.assertEqual(kode, 0)
        self.assertIn("2026-11-12", out)
        kode, out, _ = jalankan(*self._data(), "meter", "daftar")
        self.assertNotIn("2026-11-12", out)


class TestInputSalah(CliTestCase):
    def test_tanggal_duplikat_exit_1(self):
        self._isi_contoh()
        kode, _, galat = jalankan(*self._data(), "meter", "tambah",
                                  "--tanggal", "2026-11-01", "--kwh", "1200")
        self.assertEqual(kode, 1)
        self.assertIn("sudah punya bacaan", galat)

    def test_kwh_turun_exit_1(self):
        self._isi_contoh()
        kode, _, galat = jalankan(*self._data(), "meter", "tambah",
                                  "--tanggal", "2026-11-20", "--kwh", "1000")
        self.assertEqual(kode, 1)
        self.assertIn("tidak pernah turun", galat)

    def test_kwh_bukan_angka_exit_1_pesan_ramah(self):
        kode, _, galat = jalankan(*self._data(), "meter", "tambah",
                                  "--tanggal", "2026-11-01", "--kwh", "abc")
        self.assertEqual(kode, 1)
        self.assertIn("tidak valid", galat)

    def test_daya_tidak_dikenal_exit_1(self):
        kode, _, galat = jalankan(*self._data(), "daya", "atur", "1000")
        self.assertEqual(kode, 1)
        self.assertIn("tidak dikenal", galat)

    def test_daya_bukan_angka_exit_1(self):
        kode, _, galat = jalankan(*self._data(), "daya", "atur", "abc")
        self.assertEqual(kode, 1)
        self.assertIn("tidak valid", galat)

    def test_tagihan_tanpa_daya_exit_1(self):
        self._isi_contoh()
        data = model.muat(self.data)
        data["daya"] = None
        model.simpan(self.data, data)
        kode, _, galat = jalankan(*self._data(), "tagihan")
        self.assertEqual(kode, 1)
        self.assertIn("Daya belum diatur", galat)

    def test_ppj_bukan_angka_exit_1_pesan_ramah(self):
        self._isi_contoh()
        kode, _, galat = jalankan(*self._data(), "tagihan", "--ppj", "abc")
        self.assertEqual(kode, 1)
        self.assertIn("tidak valid", galat)
        self.assertIn("--ppj 3", galat)

    def test_token_beli_nominal_bukan_angka_exit_1(self):
        self._isi_contoh()
        kode, _, galat = jalankan(*self._data(), "token", "beli",
                                  "--nominal", "abc")
        self.assertEqual(kode, 1)
        self.assertIn("tidak valid", galat)
        self.assertIn("--nominal 100000", galat)

    def test_token_beli_ppj_bukan_angka_exit_1(self):
        self._isi_contoh()
        kode, _, galat = jalankan(*self._data(), "token", "beli",
                                  "--nominal", "100000", "--ppj", "abc")
        self.assertEqual(kode, 1)
        self.assertIn("tidak valid", galat)

    def test_token_beli_nominal_format_ribuan_diberi_petunjuk(self):
        # "20.000" ala Indonesia dibaca 20,0 — beri petunjuk, bukan
        # sekadar menolak karena di bawah minimum.
        self._isi_contoh()
        kode, _, galat = jalankan(*self._data(), "token", "beli",
                                  "--nominal", "20.000")
        self.assertEqual(kode, 1)
        self.assertIn("tanpa pemisah ribuan", galat)
        self.assertIn("--nominal 20000", galat)

    def test_token_ingatkan_ambang_bukan_angka_exit_1(self):
        self._isi_contoh()
        kode, _, galat = jalankan(*self._data(), "token", "ingatkan",
                                  "--ambang", "abc")
        self.assertEqual(kode, 1)
        self.assertIn("tidak valid", galat)

    def test_ppj_negatif_exit_1(self):
        self._isi_contoh()
        kode, _, galat = jalankan(*self._data(), "tagihan", "--ppj", "-3")
        self.assertEqual(kode, 1)
        self.assertIn("tidak boleh negatif", galat)

    def test_laporan_bulan_salah_exit_1(self):
        self._isi_contoh()
        for salah in ("2026-13", "11-2026", "2026-1"):
            with self.subTest(bulan=salah):
                kode, _, galat = jalankan(*self._data(), "laporan",
                                          "--bulan", salah)
                self.assertEqual(kode, 1)
                self.assertIn("tidak valid", galat)

    def test_laporan_bulan_tanpa_data_exit_1(self):
        self._isi_contoh()
        kode, _, galat = jalankan(*self._data(), "laporan", "--bulan",
                                  "2026-09")
        self.assertEqual(kode, 1)
        self.assertIn("Belum ada bacaan", galat)

    def test_pakai_tanpa_data_exit_1(self):
        kode, _, galat = jalankan(*self._data(), "pakai")
        self.assertEqual(kode, 1)
        self.assertIn("minimal 2 bacaan", galat)

    def test_hapus_nomor_tidak_ada_exit_1(self):
        self._isi_contoh()
        kode, _, galat = jalankan(*self._data(), "meter", "hapus", "99")
        self.assertEqual(kode, 1)
        self.assertIn("Tidak ada bacaan nomor 99", galat)

    def test_hapus_nomor_bukan_angka_exit_1(self):
        kode, _, galat = jalankan(*self._data(), "meter", "hapus", "abc")
        self.assertEqual(kode, 1)
        self.assertIn("tidak valid", galat)


class TestVersion(CliTestCase):
    def test_version_tampil_0_2_0(self):
        self.assertEqual(__version__, "0.2.0")
        keluar = io.StringIO()
        with redirect_stdout(keluar):
            with self.assertRaises(SystemExit) as cm:
                cli.main(["--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("listrikku 0.2.0", keluar.getvalue())


if __name__ == "__main__":
    unittest.main()
