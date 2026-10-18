import xmlrpc.client
IP_SERVER = "127.0.0.1"

def menu_gudang():
    print("="*40 + "\n      DIVISI GUDANG (RMI PROTOCOL)\n" + "="*40)
    # Menginisialisasi remote object proxy (RMI)
    server_proxy = xmlrpc.client.ServerProxy(f"http://{IP_SERVER}:8000/")
    
    while True:
        id_brg = input("\nID Barang (atau 'q'): ").strip()
        if id_brg.lower() == 'q': break
        nama = input("Nama Barang: ")
        try:
            harga = int(input("Harga: "))
            stok = int(input("Stok Masuk: "))
            # Memanggil metode objek jarak jauh seolah-olah fungsi lokal
            res = server_proxy.tambah_stok(id_brg, nama, harga, stok)
            print(f"\n[{res['status'].upper()}] {res['pesan']}")
        except Exception as e: print(f"[ERROR] {e}")
if __name__ == "__main__": menu_gudang()