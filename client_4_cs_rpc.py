import socket, pickle
from channel import Channel
IP_SERVER = "127.0.0.1"

def menu_cs():
    print("="*40 + "\n      CUSTOMER SERVICE (TCP RPC)\n" + "="*40)
    while True:
        keyword = input("\nCari barang (atau 'q'): ").strip()
        if keyword.lower() == 'q': break
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((IP_SERVER, 9090))
            ch = Channel(sock)
            ch.send_msg(pickle.dumps({"proc": "cari_barang", "params": (keyword,)}))
            res = pickle.loads(ch.recv_msg())
            ch.close()
            
            if res["status"] == "success":
                for item in res["data"]: print(f"[{item['id']}] {item['nama']} | Rp {item['harga']} | Stok: {item['stok']}")
        except Exception as e: print(f"[ERROR] {e}")
if __name__ == "__main__": menu_cs()