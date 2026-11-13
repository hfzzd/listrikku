"""Unit test token listrik prabayar ListrikKu.

Tarif: Triwulan IV 2026 (Permen ESDM No. 7/2024).
Denominasi token PLN mulai Rp20.000.
"""

import json
import os
import unittest
from datetime import date

from listrikku import model, token

CONTOH = os.path.join(os.path.dirname(__file__), "..", "contoh",
                      "listrikku-contoh.json")


def data_contoh():
    with open(CONTOH, encoding="utf-8") as f:
        return json.load(f)


class TestTokenKwh(unittest.TestCase):
    def test_semua_golongan_rumah_tangga(self):
        # Rp100.000 / tarif, dibulatkan 3 desimal (hitungan tangan).
        kasus = {
            450: ("R-1/TR subsidi", 415, 240.964),
            900: ("R-1/TR subsidi", 605, 165.289),
            1300: ("R-1/TR", 1444.70, 69.219),
            2200: ("R-1/TR", 1444.70, 69.219),
            3500: ("R-2/R-3", 1699.53, 58.840),
        }
        for daya, (golongan, tarif, kwh) in kasus.items():
            with self.subTest(daya=daya):
                hasil = token.token_kwh(100000, daya)
                self.assertEqual(hasil["golongan"], golongan)
                self.assertEqual(hasil["tarif"], tarif)
                self.assertEqual(hasil["kwh"], kwh)
                self.assertEqual(hasil["bersih"], 100000.0)

    def test_900_rtm_tarif_sendiri(self):
        # Rp100.000 / Rp1.352 = 73,964 kWh
        hasil = token.token_kwh(100000, 900, rtm=True)
        self.assertEqual(hasil["golongan"], "R-1/TR (RTM)")
        self.assertEqual(hasil["kwh"], 73.964)

    def test_ppj_dipotong_dulu(self):
        # PPJ 10%: bersih = 100.000 / 1,1 = Rp90.909,09
        # kWh = 90.909,09 / 1.444,70 = 62,926
        hasil = token.token_kwh(100000, 1300, ppj=10)
        self.assertEqual(hasil["bersih"], 90909.09)
        self.assertEqual(hasil["kwh"], 62.926)
        self.assertEqual(hasil["ppj_persen"], 10.0)

    def test_nominal_kecil_dan_batas_minimum(self):
        # Rp20.000 (batas bawah) lolos: 20.000 / 1.444,70 = 13,844 kWh
        self.assertEqual(token.token_kwh(20000, 1300)["kwh"], 13.844)
        # Rp50.000: 50.000 / 1.444,70 = 34,609 kWh
        self.assertEqual(token.token_kwh(50000, 1300)["kwh"], 34.609)

    def test_nominal_di_bawah_minimum_ditolak(self):
        for nominal in (19999, 10000, 0, -5000):
            with self.assertRaises(model.ListrikKuError, msg=str(nominal)):
                token.token_kwh(nominal, 1300)

    def test_nominal_dan_ppj_tidak_valid_ditolak(self):
        with self.assertRaises(model.ListrikKuError):
            token.token_kwh("seratus ribu", 1300)
        with self.assertRaises(model.ListrikKuError):
            token.token_kwh(100000, 1300, ppj=-5)
        with self.assertRaises(model.ListrikKuError):
            token.token_kwh(100000, 1300, ppj="x")


class TestBeliToken(unittest.TestCase):
    def test_pembelian_tersimpan_dan_terurut(self):
        data = data_contoh()
        entri, hasil = token.beli_token(data, 100000, tanggal="2026-11-01")
        self.assertEqual(entri, {"tanggal": "2026-11-01",
                                 "nominal": 100000.0, "kwh": 69.219})
        self.assertEqual(hasil["kwh"], 69.219)
        self.assertEqual(len(data["token"]), 1)
        # Beli kedua dengan tanggal lebih awal tetap tersimpan terurut.
        token.beli_token(data, 50000, tanggal="2026-10-20")
        self.assertEqual([t["tanggal"] for t in data["token"]],
                         ["2026-10-20", "2026-11-01"])

    def test_tanpa_daya_ditolak(self):
        data = model.data_kosong()
        with self.assertRaises(model.ListrikKuError):
            token.beli_token(data, 100000)

    def test_tanggal_tidak_valid_ditolak(self):
        data = data_contoh()
        with self.assertRaises(model.ListrikKuError):
            token.beli_token(data, 100000, tanggal="2026-13-01")
        with self.assertRaises(model.ListrikKuError):
            token.beli_token(data, 100000, tanggal="1 Nov 2026")


class TestSisaToken(unittest.TestCase):
    def _data_dengan_token(self):
        # Data contoh (daya 1300) + beli Rp100.000 tanggal 2026-11-01.
        data = data_contoh()
        token.beli_token(data, 100000, tanggal="2026-11-01")
        return data

    def test_sisa_kwh_hari_tersisa_tanggal_habis(self):
        # Hitungan tangan, acuan 2026-11-12:
        # token 69,219 kWh; terpakai sejak 2026-11-01 = 36 kWh
        # (periode 1-12 Nov: 36 kWh / 11 hari) -> sisa 33,219 kWh
        # rata harian 3,273 -> 33,219 / 3,273 = 10,1 hari
        # habis = 12 Nov + 10 hari = 22 Nov 2026
        hasil = token.sisa_token(self._data_dengan_token(),
                                 date(2026, 11, 12))
        self.assertEqual(hasil["dipakai_kwh"], 36.0)
        self.assertEqual(hasil["sisa_kwh"], 33.219)
        self.assertEqual(hasil["rata_harian"], 3.273)
        self.assertEqual(hasil["hari_tersisa"], 10.1)
        self.assertEqual(hasil["tanggal_habis"], "2026-11-22")
        self.assertEqual(hasil["tanggal_acuan"], "2026-11-12")
        self.assertEqual(hasil["pembelian"]["nominal"], 100000.0)

    def test_pemakaian_sejak_tanggal_tengah_periode(self):
        # Beli 2026-11-05 (tengah periode 1-12 Nov, 36 kWh / 11 hari):
        # terpakai = 36 x 7/11 = 22,909 kWh
        data = self._data_dengan_token()
        self.assertEqual(token.pemakaian_sejak(data, "2026-11-05"), 22.909)

    def test_tanpa_pembelian_ditolak_ramah(self):
        data = data_contoh()
        with self.assertRaises(model.ListrikKuError) as cm:
            token.sisa_token(data, date(2026, 11, 12))
        self.assertIn("Belum ada pembelian token", str(cm.exception))

    def test_tanpa_bacaan_ditolak_ramah(self):
        data = model.data_kosong()
        data["daya"] = 1300
        token.beli_token(data, 100000, tanggal="2026-11-01")
        with self.assertRaises(model.ListrikKuError) as cm:
            token.sisa_token(data, date(2026, 11, 12))
        self.assertIn("minimal 2 bacaan", str(cm.exception))

    def test_pembelian_terakhir_yang_dipakai(self):
        # Dua pembelian: yang terakhir (2026-11-05) yang dihitung sisanya.
        data = self._data_dengan_token()
        token.beli_token(data, 50000, tanggal="2026-11-05")
        hasil = token.sisa_token(data, date(2026, 11, 12))
        self.assertEqual(hasil["pembelian"]["tanggal"], "2026-11-05")
        # Terpakai sejak 5 Nov = 36 x 7/11 = 22,909; sisa 34,609 - 22,909
        self.assertEqual(hasil["dipakai_kwh"], 22.909)
        self.assertEqual(hasil["sisa_kwh"], 11.7)


if __name__ == "__main__":
    unittest.main()
