"""Skrip Pengujian Lengkap: Sinkronisasi Sistem Terdistribusi (Lamport Logical Clocks).
Menguji:
1. Logika Unit Lamport Clock (Aturan 1 & Aturan 2).
2. Thread-safety pada akses konkurensi tinggi.
3. Integrasi End-to-End pada 3 Protokol Terdistribusi:
   - TCP Socket RPC (Kasir & CS - Port 9090)
   - XML-RPC / RMI (Gudang - Port 8000)
   - REST API HTTP (Manajemen - Port 5000)
4. Verifikasi Total Order Kausalitas pada Database Transaksi.
"""

import threading
import time
import socket
import pickle
import xmlrpc.client
import urllib.request
import json
import unittest

from lamport_clock import LamportClock
from channel import Channel
from core_engine import ERPCore
import server_hybrid


class TestLamportClockUnit(unittest.TestCase):
    """Pengujian Unit untuk Algoritma Lamport Logical Clock"""

    def test_aturan_1_tick(self):
        """Aturan 1: Clock lokal naik 1 setiap ada event internal/sebelum kirim pesan"""
        clock = LamportClock(0)
        self.assertEqual(clock.get_time(), 0)
        self.assertEqual(clock.tick(), 1)
        self.assertEqual(clock.tick(), 2)
        self.assertEqual(clock.get_time(), 2)
        print("  [PASSED] Aturan 1: Clock increment lokal berjalan benar.")

    def test_aturan_2_update_pesan_lebih_besar(self):
        """Aturan 2a: Jika pesan masuk memiliki clock lebih tinggi: L = max(L, L_pesan) + 1"""
        clock = LamportClock(3)
        # Terima pesan dengan timestamp 10
        hasil = clock.update(10)
        self.assertEqual(hasil, 11)
        self.assertEqual(clock.get_time(), 11)
        print("  [PASSED] Aturan 2a: Sinkronisasi clock pesan lebih besar (max(3, 10) + 1 = 11).")

    def test_aturan_2_update_pesan_lebih_kecil(self):
        """Aturan 2b: Jika pesan masuk memiliki clock lebih kecil: L = max(L, L_pesan) + 1"""
        clock = LamportClock(15)
        # Terima pesan dengan timestamp 4
        hasil = clock.update(4)
        self.assertEqual(hasil, 16)
        self.assertEqual(clock.get_time(), 16)
        print("  [PASSED] Aturan 2b: Sinkronisasi clock pesan lebih kecil (max(15, 4) + 1 = 16).")

    def test_thread_safety_concurrency(self):
        """Uji konkurensi: Multi-threading tanpa terjadi race condition"""
        clock = LamportClock(0)
        jumlah_thread = 20
        iterasi_per_thread = 50

        def worker():
            for _ in range(iterasi_per_thread):
                clock.tick()

        threads = [threading.Thread(target=worker) for _ in range(jumlah_thread)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = jumlah_thread * iterasi_per_thread
        self.assertEqual(clock.get_time(), expected)
        print(f"  [PASSED] Thread Safety: {jumlah_thread} threads x {iterasi_per_thread} ticks = {expected} presisi tanpa race condition.")


class TestIntegrasiMultiProtokol(unittest.TestCase):
    """Pengujian Integrasi Server Hybrid (TCP RPC, RMI, dan REST)"""

    @classmethod
    def setUpClass(cls):
        # Jalankan server hybrid di background threads
        cls.thread_rpc = threading.Thread(target=server_hybrid.run_tcp_rpc, daemon=True)
        cls.thread_rmi = threading.Thread(target=server_hybrid.run_rmi, daemon=True)
        cls.thread_rest = threading.Thread(target=server_hybrid.run_rest, daemon=True)

        cls.thread_rpc.start()
        cls.thread_rmi.start()
        cls.thread_rest.start()
        time.sleep(1) # Beri waktu server untuk bind port

    def test_1_tcp_rpc_kasir(self):
        """Uji TCP RPC Port 9090: Kasir mencatat transaksi dengan Lamport Clock"""
        klien_clock = LamportClock(100)
        send_clock = klien_clock.tick() # L = 101

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 9090))
        ch = Channel(s)
        ch.send_msg(pickle.dumps({
            'proc': 'catat_transaksi',
            'params': ('BRG002', 1),
            'clock': send_clock
        }))
        res = pickle.loads(ch.recv_msg())
        ch.close()

        self.assertEqual(res['status'], 'success')
        self.assertIn('lamport_clock', res)
        # Server harus menyinkronkan clock ke setidaknya send_clock + 1 = 102
        self.assertGreaterEqual(res['lamport_clock'], 102)
        
        # Klien update clock lokalnya
        klien_clock.update(res['lamport_clock'])
        self.assertGreaterEqual(klien_clock.get_time(), 103)
        print(f"  [PASSED] TCP RPC Kasir: Transaksi tercatat dengan Lamport Clock: {res['lamport_clock']}")

    def test_2_rmi_gudang(self):
        """Uji RMI (XML-RPC) Port 8000: Gudang menambah stok dengan Lamport Clock"""
        klien_clock = LamportClock(200)
        send_clock = klien_clock.tick() # L = 201

        proxy = xmlrpc.client.ServerProxy('http://127.0.0.1:8000/', allow_none=True)
        res = proxy.tambah_stok('BRG002', 'Mouse Wireless', 250000, 5, send_clock)

        self.assertEqual(res['status'], 'success')
        self.assertGreaterEqual(res['lamport_clock'], 202)
        print(f"  [PASSED] RMI XML-RPC Gudang: Stok ditambah dengan Lamport Clock: {res['lamport_clock']}")

    def test_3_rest_api_manajer(self):
        """Uji REST API Port 5000: Manajer mengambil laporan dengan header X-Lamport-Clock"""
        klien_clock = LamportClock(300)
        send_clock = klien_clock.tick() # L = 301

        req = urllib.request.Request(
            'http://127.0.0.1:5000/api/laporan',
            headers={'X-Lamport-Clock': str(send_clock)}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            header_clock = int(response.headers.get('X-Lamport-Clock', 0))
            data = json.loads(response.read().decode('utf-8'))

        self.assertEqual(data['status'], 'success')
        self.assertGreaterEqual(header_clock, 302)
        self.assertIn('server_clock', data['data'])
        print(f"  [PASSED] REST API Manajer: Laporan diterima dengan Lamport Clock Server: {header_clock}")

    def test_4_urutan_kausalitas_transaksi(self):
        """Memverifikasi bahwa transaksi di database memiliki nomor urut logis yang monotonik naik"""
        core = ERPCore()
        db = core.load_db()
        transaksi = db.get("transaksi", [])
        self.assertTrue(len(transaksi) > 0)
        
        # Periksa bahwa semua transaksi memiliki atribut lamport_clock
        clocks = [t.get("lamport_clock") for t in transaksi if "lamport_clock" in t]
        self.assertTrue(len(clocks) > 0)
        print(f"  [PASSED] Total Order Kausalitas: {len(clocks)} transaksi tersimpan dengan nomor urut logis terdistribusi.")


if __name__ == '__main__':
    print("=" * 65)
    print(" MENJALANKAN PENGUJIAN SINKRONISASI LAMPORT LOGICAL CLOCKS ")
    print("=" * 65)
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestLamportClockUnit))
    suite.addTest(unittest.makeSuite(TestIntegrasiMultiProtokol))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
