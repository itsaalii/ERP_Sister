# Sistem ERP Terdistribusi Multi-Protokol dengan Sinkronisasi Lamport Logical Clocks

Proyek Sistem Terdistribusi (SISTER) yang mengimplementasikan sistem **Enterprise Resource Planning (ERP)** berbasis arsitektur multi-protokol (TCP Socket RPC, XML-RPC / RMI, dan REST HTTP) serta dilengkapi dengan **Algoritma Sinkronisasi Terdistribusi: Lamport Logical Clocks**.

---

## 1. Arsitektur & Protokol Sistem

Sistem ini memisahkan layanan bisnis ke dalam 4 modul divisi dengan protokol komunikasi yang berbeda:

| Modul / Divisi | Protokol Komunikasi | Port Server | Mekanisme & Karakteristik |
|---|---|---|---|
| **Penjualan (Kasir)** | Custom TCP Socket RPC | `:9090` | Binary framing 4-byte struct length-prefix + Serialisasi Pickle |
| **Gudang (Inventaris)** | RMI (XML-RPC) | `:8000` | Remote Method Invocation memanggil instance `ERPCore` langsung |
| **Manajemen (Laporan)** | REST API (HTTP GET) | `:5000` | Endpoint `/api/laporan` berformat JSON |
| **Layanan Pelanggan (CS)** | Custom TCP Socket RPC | `:9090` | Pencarian ketersediaan barang secara live via TCP RPC |
| **Gateway Web UI** | Web Server / Gateway | `:8080` | Dashboard terpadu HTML/JS TailwindCSS yang meneruskan request ke 3 protokol asli |

---

## 2. Konsep Sinkronisasi Terdistribusi: Lamport Logical Clocks

### Mengapa Dibutuhkan Sinkronisasi?
Dalam sistem terdistribusi riil:
1. Jam fisik (*physical clock*) antar-komputer klien dan server tidak pernah sinkron secara absolut akibat fenomena **Clock Drift**.
2. Waktu fisik lokal (`datetime.now()`) tidak dapat menjamin penentuan urutan kejadian (*event ordering*) yang adil ketika beberapa transaksi atau penambahan stok dikirimkan hampir bersamaan dari berbagai node berbeda.

### Algoritma Lamport Logical Clocks (Leslie Lamport, 1978)
Algoritma ini menggunakan nilai pencacah (*monotonic logical counter*) $L$ pada setiap proses untuk menetapkan relasi urutan kausalitas kejadian (**happens-before relation**, disimbolkan $a \to b$).

#### Aturan Algoritma:
1. **Aturan 1 (Local Event / Pre-Send):**
   Sebelum sebuah node (Klien atau Server) mengeksekusi aksi lokal atau sebelum mengirim pesan ke node lain, nilai clock dinaikkan:
   $$L = L + 1$$
2. **Aturan 2 (Message Passing & Receive):**
   Setiap pesan yang dikirim menyertakan nilai clock pengirim ($L_{pesan}$). Saat penerima menerima pesan, penerima menyinkronkan clock lokalnya:
   $$L = \max(L_{lokal}, L_{pesan}) + 1$$

### Penerapan pada Sistem ERP:
- **Klien (Kasir/Gudang/CS/Web)**: Menyimpan objek `client_clock`. Sebelum mengirim RPC/RMI/REST, klien menaikkan clock lokalnya ($L_{klien} + 1$) dan mengirimkannya ke server.
- **Server Hybrid (`server_hybrid.py`)**: Menerima request beserta timestamp klien, menyinkronkan clock server:
  $$L_{server} = \max(L_{server}, L_{klien}) + 1$$
- **Pencatatan Transaksi (`database_erp.json`)**: Setiap transaksi dicatat dengan nomor urut logis global `lamport_clock`.
- **Feedback ke Klien**: Respons server mengembalikan nilai clock terbaru, sehingga klien memperbarui clock lokalnya.

---

## 3. Struktur Berkas Proyek

```
ERP_Sister/
├── lamport_clock.py         # Modul engine Lamport Logical Clock (Thread-Safe)
├── core_engine.py           # Mesin data ERP (Inventaris, Transaksi, Mutex + Lamport Clock)
├── server_hybrid.py         # Server Hybrid multi-protokol (RPC 9090, RMI 8000, REST 5000)
├── channel.py               # Utility framing socket TCP (length-prefixed message)
├── database_erp.json        # Database lokal JSON (Inventaris, Riwayat Transaksi & Clock)
├── web_ui.py                # Gateway antarmuka web (Port 8080)
├── static/
│   └── index.html           # Antarmuka web modern dengan visualisasi live Lamport Clock
├── client_1_kasir_rpc.py    # Klien CLI Kasir (TCP RPC + Lamport Clock)
├── client_2_gudang_rmi.py   # Klien CLI Gudang (XML-RPC RMI + Lamport Clock)
├── client_3_manajer_rest.py # Klien CLI Manajer (REST API HTTP + Lamport Clock)
└── client_4_cs_rpc.py       # Klien CLI CS (TCP RPC + Lamport Clock)
```

---

## 4. Cara Menjalankan Sistem

### Langkah 1: Jalankan Server Hybrid (Terminal 1)
```bash
python server_hybrid.py
```
*Server akan mengaktifkan 3 protokol sekaligus: RPC (:9090), RMI (:8000), dan REST (:5000) serta menampilkan log sinkronisasi Lamport saat ada interaksi.*

### Langkah 2: Jalankan Web UI (Terminal 2)
```bash
python web_ui.py
```
Buka peramban (browser) di alamat: **`http://127.0.0.1:8080`**

### Langkah 3: Menjalankan Klien Konsol CLI (Opsional)
Anda dapat membuka terminal terpisah untuk menguji interaksi klien mandiri:
- **Kasir (Penjualan via TCP RPC)**:
  ```bash
  python client_1_kasir_rpc.py
  ```
- **Gudang (Restock via RMI)**:
  ```bash
  python client_2_gudang_rmi.py
  ```
- **Manajemen (Laporan via REST API)**:
  ```bash
  python client_3_manajer_rest.py
  ```
- **Customer Service (Pencarian via TCP RPC)**:
  ```bash
  python client_4_cs_rpc.py
  ```

---

## 5. Fitur Visualisasi Sinkronisasi pada Web UI

1. **Badge Lamport Clock Real-Time**:
   - Menampilkan status counter logis Klien Web ($L_{klien}$) dan Server ERP ($L_{server}$) di sidebar samping kiri.
2. **Total Ordering pada Tabel Laporan**:
   - Kolom **Lamport (L)** pada tabel 5 transaksi terakhir divisi manajemen menampilkan urutan kausalitas transaksi secara berurutan.
3. **Log Permintaan dengan Lamport Timestamp**:
   - Setiap entri riwayat permintaan menampilkan badge `Clock: L-X`, latensi milidetik, dan protokol yang digunakan.
