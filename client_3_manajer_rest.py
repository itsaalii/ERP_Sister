import urllib.request
import json
IP_SERVER = "127.0.0.1"

def menu_manajer():
    print("="*40 + "\n      DIVISI MANAJEMEN (REST API)\n" + "="*40)
    input("Tekan ENTER untuk mengirim HTTP GET Request ke Server...")
    
    try:
        # Melakukan HTTP GET ke Endpoint REST API (5000)
        url = f"http://{IP_SERVER}:5000/api/laporan"
        response = urllib.request.urlopen(url)
        res = json.loads(response.read().decode('utf-8'))
        
        if res["status"] == "success":
            data = res["data"]
            print("\n======= LAPORAN KINERJA =======")
            print(f"Total Pendapatan : Rp {data['total_pendapatan']:,}")
            print(f"Item Terjual     : {data['total_item_terjual']} Unit")
            print("\n[!] STOK KRITIS:")
            for alert in data["peringatan_stok"]: print(f" - {alert}")
    except Exception as e: print(f"[ERROR] {e}")
if __name__ == "__main__": menu_manajer()