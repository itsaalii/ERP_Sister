import xmlrpc.client
from lamport_clock import LamportClock

IP_SERVER = "127.0.0.1"
client_clock = LamportClock(0)

def menu_gudang():
    print("="*48)
    print("      DIVISI GUDANG (RMI PROTOCOL + LAMPORT CLOCK)")
    print("="*48)
    server_proxy = xmlrpc.client.ServerProxy(f"http://{IP_SERVER}:8000/")
    
    while True:
        print(f"\n[Status Clock Klien: {client_clock.get_time()}]")
        id_brg = input("ID Barang (atau 'q'): ").strip()
        if id_brg.lower() == 'q':
            break
        nama = input("Nama Barang: ")
        try:
            harga = int(input("Harga: "))
            stok = int(input("Stok Masuk: "))
            
            # Aturan 1: Naikkan clock lokal sebelum memanggil remote method
            current_clock = client_clock.tick()
            
            # Panggil remote method RMI dengan menyertakan clock lokal
            res = server_proxy.tambah_stok(id_brg, nama, harga, stok, current_clock)
            
            # Aturan 2: Sinkronisasikan clock lokal dengan balasan server
            srv_clock = res.get("lamport_clock", res.get("server_clock", 0))
            new_clock = client_clock.update(srv_clock)
            
            print(f"\n[{res['status'].upper()}] {res['pesan']}")
            print(f"[SYNC] Lamport Clock Event: {res.get('lamport_clock', '-')} | Clock Klien Terkini: {new_clock}")
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    menu_gudang()