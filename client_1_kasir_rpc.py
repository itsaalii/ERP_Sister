import socket, pickle
from channel import Channel
from lamport_clock import LamportClock

IP_SERVER = "127.0.0.1"
client_clock = LamportClock(0)

def menu_kasir():
    print("="*48)
    print("      DIVISI PENJUALAN (TCP RPC + LAMPORT CLOCK)")
    print("="*48)
    while True:
        print(f"\n[Status Clock Klien: {client_clock.get_time()}]")
        id_brg = input("ID Barang (atau 'q'): ").strip()
        if id_brg.lower() == 'q':
            break
        try:
            qty = int(input("Jumlah: "))
            # Aturan 1: Naikkan clock sebelum mengirim pesan
            current_clock = client_clock.tick()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((IP_SERVER, 9090))
            ch = Channel(sock)
            # Sertakan clock lokal dalam payload RPC
            ch.send_msg(pickle.dumps({
                "proc": "catat_transaksi",
                "params": (id_brg, qty),
                "clock": current_clock
            }))
            res = pickle.loads(ch.recv_msg())
            ch.close()
            
            # Aturan 2: Sinkronisasikan clock lokal dengan clock balasan dari server
            srv_clock = res.get("lamport_clock", res.get("server_clock", 0))
            new_clock = client_clock.update(srv_clock)
            
            if res["status"] == "success":
                data = res["data"]
                print(f"\n[STRUK] {data['id_transaksi']} | {data['nama_barang']} x{data['qty']} | Rp {data['total_harga']:,}")
                print(f"[SYNC] Lamport Clock Transaksi: {data.get('lamport_clock', '-')} | Clock Klien Terkini: {new_clock}")
            else:
                print(f"[GAGAL] {res['pesan']} (Clock Klien Disinkronkan: {new_clock})")
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    menu_kasir()