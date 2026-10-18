"""Gateway Web UI.
Menyajikan antarmuka web (static/index.html) dan meneruskan aksi pengguna ke server_hybrid.py
menggunakan protokol aslinya: TCP RPC (9090), XML-RPC/RMI (8000), dan REST (5000).
Jalankan: python server_hybrid.py  (terminal 1)  lalu  python web_ui.py  (terminal 2) -> http://127.0.0.1:8080
"""
import os, json, socket, pickle, time, urllib.request, xmlrpc.client
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from channel import Channel

IP_SERVER = "127.0.0.1"
WEB_PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def tcp_rpc(proc, params):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((IP_SERVER, 9090))
    ch = Channel(sock)
    try:
        ch.send_msg(pickle.dumps({"proc": proc, "params": params}))
        return pickle.loads(ch.recv_msg())
    finally:
        ch.close()


def rmi_call(method, *args):
    proxy = xmlrpc.client.ServerProxy(f"http://{IP_SERVER}:8000/", allow_none=True)
    return getattr(proxy, method)(*args)


def rest_get(path):
    with urllib.request.urlopen(f"http://{IP_SERVER}:5000{path}", timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


def port_open(port):
    try:
        with socket.create_connection((IP_SERVER, port), timeout=0.6):
            return True
    except OSError:
        return False


def timed(protocol, fn):
    t = time.perf_counter()
    try:
        res = fn()
    except Exception as e:
        res = {"status": "error", "pesan": f"Tidak dapat terhubung ke server ({protocol}): {e}"}
    res["_meta"] = {"protocol": protocol, "ms": round((time.perf_counter() - t) * 1000, 1)}
    return res


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/status":
            return self._json({"rpc": port_open(9090), "rmi": port_open(8000), "rest": port_open(5000)})
        if u.path == "/api/cari":
            kw = q.get("q", [""])[0]
            return self._json(timed("TCP RPC", lambda: tcp_rpc("cari_barang", (kw,))))
        if u.path == "/api/laporan":
            return self._json(timed("REST", lambda: rest_get("/api/laporan")))
        # static files
        name = "index.html" if u.path in ("/", "") else u.path.lstrip("/")
        fp = os.path.normpath(os.path.join(STATIC_DIR, name))
        if fp.startswith(STATIC_DIR) and os.path.isfile(fp):
            ctype = "text/html; charset=utf-8" if fp.endswith(".html") else "application/octet-stream"
            with open(fp, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json({"status": "error", "pesan": "Body JSON tidak valid"}, 400)
        path = urlparse(self.path).path
        try:
            if path == "/api/transaksi":
                idb, qty = str(body["id_barang"]).strip(), int(body["qty"])
                return self._json(timed("TCP RPC", lambda: tcp_rpc("catat_transaksi", (idb, qty))))
            if path == "/api/stok":
                a = (str(body["id_barang"]).strip(), str(body["nama"]), int(body["harga"]), int(body["stok"]))
                return self._json(timed("RMI (XML-RPC)", lambda: rmi_call("tambah_stok", *a)))
        except (KeyError, ValueError) as e:
            return self._json({"status": "error", "pesan": f"Input tidak valid: {e}"}, 400)
        self._json({"status": "error", "pesan": "Endpoint tidak ditemukan"}, 404)


if __name__ == "__main__":
    print(f"Web UI ERP berjalan di http://127.0.0.1:{WEB_PORT}")
    try:
        ThreadingHTTPServer(("0.0.0.0", WEB_PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nWeb UI dimatikan.")
