import json, os, uuid, threading
from datetime import datetime
from lamport_clock import LamportClock

DB_FILE = "database_erp.json"

class ERPCore:
    """Mesin utama (State) ERP Terdistribusi.
    Dilindungi dengan Mutex Lock untuk thread-safety lokal dan
    Lamport Logical Clock untuk sinkronisasi urutan kejadian (happens-before) terdistribusi.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.db = self.load_db()
        # Inisialisasi Lamport Clock dari database atau nilai tertinggi transaksi yang tersimpan
        initial_clock = self.db.get("server_clock", 0)
        if self.db.get("transaksi"):
            max_trx_clock = max([t.get("lamport_clock", 0) for t in self.db["transaksi"]] + [0])
            initial_clock = max(initial_clock, max_trx_clock)
        self.clock = LamportClock(initial_clock)

    def load_db(self):
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                return data
        return {
            "inventaris": {
                "BRG001": {"nama": "Laptop Asus ROG", "harga": 15000000, "stok": 10},
                "BRG002": {"nama": "Mouse Wireless", "harga": 250000, "stok": 50}
            },
            "transaksi": [],
            "server_clock": 0
        }

    def save_db(self):
        self.db["server_clock"] = self.clock.get_time()
        with open(DB_FILE, 'w') as f:
            json.dump(self.db, f, indent=4)

    def get_server_clock(self):
        return self.clock.get_time()

    def tambah_stok(self, id_barang, nama, harga, tambahan_stok, client_clock=0):
        with self.lock: # Cegah race condition lokal
            # Aturan Lamport: L_server = max(L_server, L_klien) + 1
            event_clock = self.clock.update(client_clock)
            id_barang = id_barang.upper()
            inv = self.db["inventaris"]
            if id_barang in inv:
                inv[id_barang]["stok"] += tambahan_stok
                inv[id_barang]["harga"] = harga
                inv[id_barang]["last_sync_clock"] = event_clock
                msg = f"Stok {id_barang} berhasil ditambahkan."
            else:
                inv[id_barang] = {
                    "nama": nama,
                    "harga": harga,
                    "stok": tambahan_stok,
                    "last_sync_clock": event_clock
                }
                msg = f"Barang baru {id_barang} berhasil didaftarkan."
            self.save_db()
            return {"status": "success", "pesan": msg, "lamport_clock": event_clock}

    def cari_barang(self, keyword, client_clock=0):
        with self.lock:
            event_clock = self.clock.update(client_clock)
            keyword = keyword.lower()
            hasil = [
                {"id": k, **v}
                for k, v in self.db["inventaris"].items()
                if keyword in v["nama"].lower() or keyword in k.lower()
            ]
            return {"status": "success", "data": hasil, "lamport_clock": event_clock}

    def catat_transaksi(self, id_barang, qty, client_clock=0):
        with self.lock:
            id_barang = id_barang.upper()
            inv = self.db["inventaris"]
            if id_barang not in inv:
                event_clock = self.clock.update(client_clock)
                return {"status": "error", "pesan": "ID Barang tidak ditemukan.", "lamport_clock": event_clock}
            if inv[id_barang]["stok"] < qty:
                event_clock = self.clock.update(client_clock)
                return {"status": "error", "pesan": f"Stok tidak cukup! Sisa: {inv[id_barang]['stok']}", "lamport_clock": event_clock}
            
            # Sinkronisasi Lamport Clock untuk event transaksi
            event_clock = self.clock.update(client_clock)
            inv[id_barang]["stok"] -= qty
            inv[id_barang]["last_sync_clock"] = event_clock
            total_harga = inv[id_barang]["harga"] * qty
            record = {
                "id_transaksi": "TRX-" + str(uuid.uuid4())[:8].upper(),
                "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "lamport_clock": event_clock,
                "id_barang": id_barang,
                "nama_barang": inv[id_barang]["nama"],
                "qty": qty,
                "total_harga": total_harga
            }
            self.db["transaksi"].append(record)
            self.save_db()
            return {"status": "success", "data": record, "lamport_clock": event_clock}

    def laporan_keuangan(self, client_clock=0):
        with self.lock:
            event_clock = self.clock.update(client_clock)
            trx = self.db.get("transaksi", [])
            stok_kritis = [f"{k} ({v['nama']}) - Sisa {v['stok']}" for k, v in self.db["inventaris"].items() if v["stok"] < 10]
            return {
                "status": "success",
                "lamport_clock": event_clock,
                "data": {
                    "total_transaksi": len(trx),
                    "total_pendapatan": sum(t.get("total_harga", 0) for t in trx),
                    "total_item_terjual": sum(t.get("qty", 0) for t in trx),
                    "peringatan_stok": stok_kritis,
                    "riwayat_terakhir": trx[-5:],
                    "server_clock": event_clock
                }
            }
