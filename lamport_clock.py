"""Modul Sinkronisasi Sistem Terdistribusi: Algoritma Lamport Logical Clocks.

Algoritma ini diusulkan oleh Leslie Lamport (1978) untuk menentukan urutan kejadian (happens-before relation)
dalam sistem terdistribusi tanpa bergantung pada jam fisik (physical clock) yang rentan terhadap clock drift.

Aturan Algoritma:
1. Sebelum proses/node melakukan aksi lokal atau mengirim pesan:
   L = L + 1
2. Saat pesan dikirim, nilai L saat ini disertakan ke dalam pesan.
3. Saat pesan diterima dengan timestamp L_pesan:
   L = max(L_lokal, L_pesan) + 1
"""

import threading

class LamportClock:
    def __init__(self, initial_value: int = 0):
        self._clock = int(initial_value)
        self._lock = threading.Lock()

    def get_time(self) -> int:
        """Mengambil nilai waktu logis saat ini tanpa menaikkannya."""
        with self._lock:
            return self._clock

    def tick(self) -> int:
        """Aturan 1: Naikkan clock lokal untuk event internal atau sebelum mengirim pesan."""
        with self._lock:
            self._clock += 1
            return self._clock

    def update(self, received_time: int) -> int:
        """Aturan 2: Sinkronisasikan clock lokal dengan clock pesan yang diterima.
        Formula: L = max(L_lokal, L_pesan) + 1
        """
        with self._lock:
            try:
                rec = int(received_time)
            except (ValueError, TypeError):
                rec = 0
            self._clock = max(self._clock, rec) + 1
            return self._clock

    def __str__(self) -> str:
        return f"LamportClock({self.get_time()})"
