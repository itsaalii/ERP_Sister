import json, os, uuid, threading
from datetime import datetime

DB_FILE = "database_erp.json"

class ERPCore:
    """Mesin utama (State) yang dilindungi dengan Mutex Lock agar aman diakses oleh 3 Protokol secara bersamaan (Thread-Safe)"""
    def __init__(self):
        self.lock = threading.Lock()
        self.db = self.load_db()

    def load_db(self):
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r') as f: return json.load(f)
        return {
            "inventaris": {
                "BRG001": {"nama": "Laptop Asus ROG", "harga": 15000000, "stok": 10},
                "BRG002": {"nama": "Mouse Wireless", "harga": 250000, "stok": 50}
            },
            "transaksi": []
        }

    def save_db(self):
        with open(DB_FILE, 'w') as f: json.dump(self.db, f, indent=4)

    def tambah_stok(self, id_barang, nama, harga, tambahan_stok):
        with self.lock: # Cegah race condition
            id_barang = id_barang.upper()
            inv = self.db["inventaris"]
            if id_barang in inv:
                inv[id_barang]["stok"] += tambahan_stok
                inv[id_barang]["harga"] = harga
                msg = f"Stok {id_barang} berhasil ditambahkan."
            else:
                inv[id_barang] = {"nama": nama, "harga": harga, "stok": tambahan_stok}
                msg = f"Barang baru {id_barang} berhasil didaftarkan."
            self.save_db()
            return {"status": "success", "pesan": msg}

    def cari_barang(self, keyword):
        with self.lock:
            keyword = keyword.lower()
            hasil = [{"id": k, **v} for k, v in self.db["inventaris"].items() if keyword in v["nama"].lower() or keyword in k.lower()]
            return {"status": "success", "data": hasil}

    def catat_transaksi(self, id_barang, qty):
        with self.lock:
            id_barang = id_barang.upper()
            inv = self.db["inventaris"]
            if id_barang not in inv: return {"status": "error", "pesan": "ID Barang tidak ditemukan."}
            if inv[id_barang]["stok"] < qty: return {"status": "error", "pesan": f"Stok tidak cukup! Sisa: {inv[id_barang]['stok']}"}
            
            inv[id_barang]["stok"] -= qty
            total_harga = inv[id_barang]["harga"] * qty
            record = {
                "id_transaksi": "TRX-" + str(uuid.uuid4())[:8].upper(),
                "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "id_barang": id_barang,
                "nama_barang": inv[id_barang]["nama"],
                "qty": qty, "total_harga": total_harga
            }
            self.db["transaksi"].append(record)
            self.save_db()
            return {"status": "success", "data": record}

    def laporan_keuangan(self):
        with self.lock:
            trx = self.db["transaksi"]
            stok_kritis = [f"{k} ({v['nama']}) - Sisa {v['stok']}" for k, v in self.db["inventaris"].items() if v["stok"] < 10]
            return {
                "status": "success",
                "data": {
                    "total_transaksi": len(trx),
                    "total_pendapatan": sum(t["total_harga"] for t in trx),
                    "total_item_terjual": sum(t["qty"] for t in trx),
                    "peringatan_stok": stok_kritis,
                    "riwayat_terakhir": trx[-5:]
                }
            }
