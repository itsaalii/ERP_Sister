import threading
import socket, pickle, json
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
    print("[RPC TCP] Berjalan di Port 9090 (Untuk Kasir & CS)")
    while True:
        client, _ = sock.accept()
        ch = Channel(client)
        try:
            raw = ch.recv_msg()
            if raw:
                req = pickle.loads(raw)
                proc = req.get("proc")
                params = req.get("params", ())
                method = getattr(core, proc, None)
                res = method(*params) if callable(method) else {"status": "error", "pesan": "Metode Invalid"}
                ch.send_msg(pickle.dumps(res))
        except Exception: pass
        finally: ch.close()

# --- 2. PELADEN RMI (XML-RPC) - PORT 8000 ---
def run_rmi():
    # Mendaftarkan instance objek Core langsung agar dapat dipanggil dari jarak jauh
    server = SimpleXMLRPCServer((HOST, 8000), allow_none=True, logRequests=False)
    server.register_instance(core)
    print("[RMI API] Berjalan di Port 8000 (Untuk Gudang)")
    server.serve_forever()

# --- 3. PELADEN REST API (HTTP) - PORT 5000 ---
class RESTHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass # Matikan log bawaan
    def do_GET(self):
        if self.path == '/api/laporan':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            res = core.laporan_keuangan()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_rest():
    server = HTTPServer((HOST, 5000), RESTHandler)
    print("[REST API] Berjalan di Port 5000 (Untuk Manajer)")
    server.serve_forever()

if __name__ == "__main__":
    print("="*50)
    print(" MEMULAI HYBRID MULTI-PROTOCOL SERVER ERP ")
    print("="*50)
    # Menjalankan ketiga server secara paralel (Multi-threading)
    threading.Thread(target=run_tcp_rpc, daemon=True).start()
    threading.Thread(target=run_rmi, daemon=True).start()
    threading.Thread(target=run_rest, daemon=True).start()
    
    try:
        while True: pass # Biarkan main thread hidup
    except KeyboardInterrupt:
        print("\nServer dimatikan.")
