import threading
import socket, pickle, json
from urllib.parse import urlparse, parse_qs
from xmlrpc.server import SimpleXMLRPCServer
from http.server import BaseHTTPRequestHandler, HTTPServer
from core_engine import ERPCore
from channel import Channel

core = ERPCore()
HOST = "0.0.0.0"

# --- 1. PELADEN RPC KUSTOM (TCP) - PORT 9090 ---
def run_tcp_rpc():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, 9090))
    sock.listen(10)
    print(f"[RPC TCP]  Berjalan di Port 9090 (Kasir & CS) | Lamport Clock Awal: {core.get_server_clock()}")
    while True:
        client, _ = sock.accept()
        ch = Channel(client)
        try:
            raw = ch.recv_msg()
            if raw:
                req = pickle.loads(raw)
                proc = req.get("proc")
                params = list(req.get("params", ()))
                client_clock = int(req.get("clock", 0))

                # Jika parameter belum menyertakan client_clock, teruskan dari payload
                if proc == "catat_transaksi" and len(params) == 2:
                    params.append(client_clock)
                elif proc == "cari_barang" and len(params) == 1:
                    params.append(client_clock)
                elif proc == "tambah_stok" and len(params) == 4:
                    params.append(client_clock)
                elif proc == "laporan_keuangan" and len(params) == 0:
                    params.append(client_clock)

                method = getattr(core, proc, None)
                res = method(*params) if callable(method) else {"status": "error", "pesan": "Metode Invalid"}
                if isinstance(res, dict):
                    res["server_clock"] = core.get_server_clock()

                print(f"[SYNC LAMPORT - RPC TCP] Proc: {proc:<15} | Clock Klien: {client_clock:<3} -> Clock Server: {core.get_server_clock()}")
                ch.send_msg(pickle.dumps(res))
        except Exception as e:
            pass
        finally:
            ch.close()

# --- 2. PELADEN RMI (XML-RPC) - PORT 8000 ---
class RMIWrapper:
    """Wrapper untuk memonitor dan mencatat sinkronisasi Lamport Clock pada RMI"""
    def __init__(self, erp_core):
        self.core = erp_core

    def tambah_stok(self, id_barang, nama, harga, tambahan_stok, client_clock=0):
        res = self.core.tambah_stok(id_barang, nama, harga, tambahan_stok, client_clock)
        res["server_clock"] = self.core.get_server_clock()
        print(f"[SYNC LAMPORT - RMI]     Proc: tambah_stok     | Clock Klien: {client_clock:<3} -> Clock Server: {self.core.get_server_clock()}")
        return res

    def cari_barang(self, keyword, client_clock=0):
        res = self.core.cari_barang(keyword, client_clock)
        res["server_clock"] = self.core.get_server_clock()
        print(f"[SYNC LAMPORT - RMI]     Proc: cari_barang     | Clock Klien: {client_clock:<3} -> Clock Server: {self.core.get_server_clock()}")
        return res

    def catat_transaksi(self, id_barang, qty, client_clock=0):
        res = self.core.catat_transaksi(id_barang, qty, client_clock)
        res["server_clock"] = self.core.get_server_clock()
        print(f"[SYNC LAMPORT - RMI]     Proc: catat_transaksi | Clock Klien: {client_clock:<3} -> Clock Server: {self.core.get_server_clock()}")
        return res

    def laporan_keuangan(self, client_clock=0):
        res = self.core.laporan_keuangan(client_clock)
        res["server_clock"] = self.core.get_server_clock()
        print(f"[SYNC LAMPORT - RMI]     Proc: laporan         | Clock Klien: {client_clock:<3} -> Clock Server: {self.core.get_server_clock()}")
        return res

    def get_server_clock(self):
        return self.core.get_server_clock()

def run_rmi():
    server = SimpleXMLRPCServer((HOST, 8000), allow_none=True, logRequests=False)
    server.register_instance(RMIWrapper(core))
    print(f"[RMI API]  Berjalan di Port 8000 (Gudang)      | Lamport Clock Awal: {core.get_server_clock()}")
    server.serve_forever()

# --- 3. PELADEN REST API (HTTP) - PORT 5000 ---
class RESTHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Matikan log default

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        # Ambil client clock dari header HTTP atau query string
        client_clock_header = self.headers.get('X-Lamport-Clock')
        client_clock_query = q.get('clock', [None])[0]
        try:
            client_clock = int(client_clock_header or client_clock_query or 0)
        except ValueError:
            client_clock = 0

        if u.path == '/api/laporan':
            res = core.laporan_keuangan(client_clock)
            res["server_clock"] = core.get_server_clock()
            print(f"[SYNC LAMPORT - REST]    Path: /api/laporan    | Clock Klien: {client_clock:<3} -> Clock Server: {core.get_server_clock()}")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('X-Lamport-Clock', str(core.get_server_clock()))
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        elif u.path == '/api/clock':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('X-Lamport-Clock', str(core.get_server_clock()))
            self.end_headers()
            self.wfile.write(json.dumps({"server_clock": core.get_server_clock()}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_rest():
    server = HTTPServer((HOST, 5000), RESTHandler)
    print(f"[REST API] Berjalan di Port 5000 (Manajer)     | Lamport Clock Awal: {core.get_server_clock()}")
    server.serve_forever()

if __name__ == "__main__":
    print("="*60)
    print(" MEMULAI HYBRID MULTI-PROTOCOL SERVER ERP (SINKRONISASI LAMPORT)")
    print("="*60)
    # Menjalankan ketiga server secara paralel (Multi-threading)
    threading.Thread(target=run_tcp_rpc, daemon=True).start()
    threading.Thread(target=run_rmi, daemon=True).start()
    threading.Thread(target=run_rest, daemon=True).start()
    
    try:
        while True: pass # Biarkan main thread hidup
    except KeyboardInterrupt:
        print("\nServer dimatikan.")
