import socket, pickle
from channel import Channel
IP_SERVER = "127.0.0.1"

def menu_kasir():
    print("="*40 + "\n      DIVISI PENJUALAN (TCP RPC)\n" + "="*40)
    while True:
        id_brg = input("\nID Barang (atau 'q'): ").strip()
        if id_brg.lower() == 'q': break
        try:
            qty = int(input("Jumlah: "))
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((IP_SERVER, 9090)) # Menggunakan Protokol RPC (9090)
            ch = Channel(sock)
            ch.send_msg(pickle.dumps({"proc": "catat_transaksi", "params": (id_brg, qty)}))
            res = pickle.loads(ch.recv_msg())
            ch.close()
            
            if res["status"] == "success":
                data = res["data"]
                print(f"\n[STRUK] {data['id_transaksi']} | {data['nama_barang']} x{data['qty']} | Rp {data['total_harga']:,}")
            else: print(f"[GAGAL] {res['pesan']}")
        except Exception as e: print(f"[ERROR] {e}")
if __name__ == "__main__": menu_kasir()