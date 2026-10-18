import socket, pickle
from channel import Channel
from lamport_clock import LamportClock

IP_SERVER = "127.0.0.1"
client_clock = LamportClock(0)

def menu_cs():
    print("="*48)
    print("      CUSTOMER SERVICE (TCP RPC + LAMPORT CLOCK)")
    print("="*48)
    while True:
        print(f"\n[Status Clock Klien: {client_clock.get_time()}]")
        keyword = input("Cari barang (kosongkan untuk semua, atau 'q' keluar): ").strip()
        if keyword.lower() == 'q':
            break
        try:
            # Aturan 1: Naikkan clock lokal sebelum kirim RPC
            current_clock = client_clock.tick()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((IP_SERVER, 9090))
            ch = Channel(sock)
            ch.send_msg(pickle.dumps({
                "proc": "cari_barang",
                "params": (keyword,),
                "clock": current_clock
            }))
            res = pickle.loads(ch.recv_msg())
            ch.close()
            
            # Aturan 2: Sinkronisasikan clock lokal dengan server
            srv_clock = res.get("lamport_clock", res.get("server_clock", 0))
            new_clock = client_clock.update(srv_clock)
            
            if res.get("status") == "success":
                data = res.get("data", [])
                print(f"\n[HASIL PENCARIAN] Total: {len(data)} barang | Clock Event: {srv_clock} | Clock Klien: {new_clock}")
                for item in data:
                    print(f" - [{item['id']}] {item['nama']} | Rp {item['harga']:,} | Stok: {item['stok']}")
            else:
                print(f"[GAGAL] {res.get('pesan')}")
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    menu_cs()