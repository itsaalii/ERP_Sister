import urllib.request
import json
from lamport_clock import LamportClock

IP_SERVER = "127.0.0.1"
client_clock = LamportClock(0)

def menu_manajer():
    print("="*52)
    print("      DIVISI MANAJEMEN (REST API + LAMPORT CLOCK)")
    print("="*52)
    
    while True:
        print(f"\n[Status Clock Klien: {client_clock.get_time()}]")
        pilihan = input("Tekan [ENTER] untuk Request Laporan (atau 'q' keluar): ").strip()
        if pilihan.lower() == 'q':
            break
        
        try:
            # Aturan 1: Naikkan clock lokal sebelum mengirim HTTP Request
            current_clock = client_clock.tick()
            
            # Melakukan HTTP GET ke Endpoint REST API (5000) dengan header X-Lamport-Clock
            url = f"http://{IP_SERVER}:5000/api/laporan"
            req = urllib.request.Request(url, headers={"X-Lamport-Clock": str(current_clock)})
            
            with urllib.request.urlopen(req, timeout=5) as response:
                srv_clock_header = response.headers.get("X-Lamport-Clock", "0")
                res = json.loads(response.read().decode('utf-8'))
            
            # Aturan 2: Sinkronisasikan clock lokal dengan clock response server
            srv_clock = int(srv_clock_header or res.get("lamport_clock", 0))
            new_clock = client_clock.update(srv_clock)
            
            if res.get("status") == "success":
                data = res["data"]
                print("\n" + "="*30 + " LAPORAN KINERJA " + "="*30)
                print(f"Total Pendapatan  : Rp {data['total_pendapatan']:,}")
                print(f"Total Transaksi   : {data['total_transaksi']}")
                print(f"Item Terjual      : {data['total_item_terjual']} Unit")
                print(f"Lamport Clock Srv : {data.get('server_clock', srv_clock)}")
                print(f"Lamport Clock Kln : {new_clock}")
                
                print("\n[!] STOK KRITIS:")
                if data["peringatan_stok"]:
                    for alert in data["peringatan_stok"]:
                        print(f" - {alert}")
                else:
                    print(" - Semua stok aman.")
                
                print("\n[!] 5 TRANSAKSI TERAKHIR (URUTAN KAUSALITAS LAMPORT):")
                if data.get("riwayat_terakhir"):
                    for trx in reversed(data["riwayat_terakhir"]):
                        trx_clock = trx.get("lamport_clock", "-")
                        print(f" - [{trx['id_transaksi']}] L-{trx_clock} | {trx['waktu']} | {trx['nama_barang']} x{trx['qty']} = Rp {trx['total_harga']:,}")
                else:
                    print(" - Belum ada riwayat transaksi.")
            else:
                print(f"[GAGAL] {res.get('pesan')}")
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    menu_manajer()