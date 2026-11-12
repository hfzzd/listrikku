"""Unit test tarif PLN + estimasi tagihan ListrikKu.

Tarif: Triwulan IV 2026 (Permen ESDM No. 7/2024).
"""

import json
import os
import unittest

from listrikku import model, tarif

CONTOH = os.path.join(os.path.dirname(__file__), "..", "contoh",
                      "listrikku-contoh.json")


def data_contoh():
    with open(CONTOH, encoding="utf-8") as f:
        return json.load(f)


class TestGolonganDanTarif(unittest.TestCase):
    def test_semua_golongan_rumah_tangga(self):
        kasus = {
            450: ("R-1/TR subsidi", 415),
            900: ("R-1/TR subsidi", 605),
            1300: ("R-1/TR", 1444.70),
            2200: ("R-1/TR", 1444.70),
            3500: ("R-2/R-3", 1699.53),
            4400: ("R-2/R-3", 1699.53),
            200000: ("R-2/R-3", 1699.53),
        }
        for daya, harapan in kasus.items():
            with self.subTest(daya=daya):
                self.assertEqual(tarif.golongan_dan_tarif(daya), harapan)

    def test_900_rtm_tarif_sendiri(self):
        self.assertEqual(tarif.golongan_dan_tarif(900, rtm=True),
                         ("R-1/TR (RTM)", 1352))

    def test_daya_tidak_dikenal_ditolak(self):
        for daya in (1000, 5500 - 5500 + 100, 300, 0, -1300, 200001, "abc"):
            with self.assertRaises(model.ListrikKuError, msg=str(daya)):
                tarif.golongan_dan_tarif(daya)


class TestAturDaya(unittest.TestCase):
    def test_rtm_hanya_untuk_900(self):
        data = model.data_kosong()
        with self.assertRaises(model.ListrikKuError):
            tarif.atur_daya(data, 1300, rtm=True)
        tarif.atur_daya(data, 900, rtm=True)
        self.assertEqual((data["daya"], data["rtm"]), (900, True))

    def test_daya_tidak_valid_tidak_menyimpan(self):
        data = model.data_kosong()
        with self.assertRaises(model.ListrikKuError):
            tarif.atur_daya(data, "abc")
        self.assertIsNone(data["daya"])


class TestRekeningMinimum(unittest.TestCase):
    def test_40_jam_nyala(self):
        # 40 jam x 1300 VA / 1000 = 52 kWh; 40 x 900 / 1000 = 36 kWh
        self.assertEqual(tarif.rekening_minimum_kwh(1300), 52.0)
        self.assertEqual(tarif.rekening_minimum_kwh(900), 36.0)
        self.assertEqual(tarif.rekening_minimum_kwh(450), 18.0)


class TestHitungTagihan(unittest.TestCase):
    def test_tagihan_normal_1300(self):
        # 100 kWh x Rp1.444,70 = Rp144.470
        hasil = tarif.hitung_tagihan(100, 1300)
        self.assertEqual(hasil["biaya"], 144470.0)
        self.assertEqual(hasil["total"], 144470.0)
        self.assertEqual(hasil["ditagih_kwh"], 100)
        self.assertFalse(hasil["di_bawah_minimum"])

    def test_di_bawah_minimum_ditagih_minimum(self):
        # 10 kWh < 52 kWh minimum -> ditagih 52 x Rp1.444,70 = Rp75.124,40
        hasil = tarif.hitung_tagihan(10, 1300)
        self.assertTrue(hasil["di_bawah_minimum"])
        self.assertEqual(hasil["ditagih_kwh"], 52.0)
        self.assertEqual(hasil["biaya"], 75124.40)

    def test_ppj_ditambah_setelah_biaya(self):
        # 100 kWh -> Rp144.470; PPJ 3% = Rp4.334,10; total Rp148.804,10
        hasil = tarif.hitung_tagihan(100, 1300, ppj=3)
        self.assertEqual(hasil["ppj_rp"], 4334.10)
        self.assertEqual(hasil["total"], 148804.10)

    def test_900_subsidi_dan_rtm(self):
        # 100 kWh: subsidi 100 x 605 = Rp60.500; RTM 100 x 1352 = Rp135.200
        self.assertEqual(tarif.hitung_tagihan(100, 900)["biaya"], 60500.0)
        self.assertEqual(
            tarif.hitung_tagihan(100, 900, rtm=True)["biaya"], 135200.0)

    def test_450_subsidi(self):
        self.assertEqual(tarif.hitung_tagihan(100, 450)["biaya"], 41500.0)

    def test_3500_ke_atas(self):
        # 200 kWh x Rp1.699,53 = Rp339.906 (di atas minimum 140 kWh)
        self.assertEqual(tarif.hitung_tagihan(200, 3500)["biaya"], 339906.0)
        # 100 kWh < minimum 140 kWh -> ditagih 140 x Rp1.699,53
        hasil = tarif.hitung_tagihan(100, 3500)
        self.assertTrue(hasil["di_bawah_minimum"])
        self.assertEqual(hasil["biaya"], 237934.20)

    def test_ppj_negatif_dan_pemakaian_negatif_ditolak(self):
        with self.assertRaises(model.ListrikKuError):
            tarif.hitung_tagihan(100, 1300, ppj=-1)
        with self.assertRaises(model.ListrikKuError):
            tarif.hitung_tagihan(-5, 1300)


class TestProyeksiBulanBerjalan(unittest.TestCase):
    def test_kurang_dari_dua_bacaan_ditolak(self):
        from datetime import date
        data = model.data_kosong()
        model.tambah_bacaan(data, "2026-11-01", 1000.0)
        with self.assertRaises(model.ListrikKuError):
            tarif.proyeksi_bulan_berjalan(data, date(2026, 11, 12))

    def test_proyeksi_dari_bacaan_bulan_ini(self):
        # Rata Nov data contoh 3,273 kWh/hari x 30 hari = 98,19 kWh
        from datetime import date
        hasil = tarif.proyeksi_bulan_berjalan(data_contoh(),
                                              date(2026, 11, 12))
        self.assertEqual(hasil["rata_harian"], 3.273)
        self.assertEqual(hasil["proyeksi_kwh"], 98.19)
        self.assertEqual(hasil["sumber"], "bulan ini")

    def test_proyeksi_pakai_periode_terakhir_bila_belum_ada_bacaan_bulan_ini(self):
        # Hanya bacaan Oktober: rata periode terakhir 54/17 = 3,176
        from datetime import date
        data = model.data_kosong()
        model.tambah_bacaan(data, "2026-10-15", 1050.0)
        model.tambah_bacaan(data, "2026-11-01", 1104.0)
        hasil = tarif.proyeksi_bulan_berjalan(data, date(2026, 11, 12))
        self.assertEqual(hasil["sumber"], "periode terakhir")
        self.assertEqual(hasil["rata_harian"], 3.176)
        self.assertEqual(hasil["proyeksi_kwh"], 95.28)


if __name__ == "__main__":
    unittest.main()
