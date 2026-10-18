import socket
import struct

class Channel:
    def __init__(self, sock: socket.socket):
        self.sock = sock

    def send_msg(self, data: bytes):
        header = struct.pack("!I", len(data))
        self.sock.sendall(header + data)

    def recv_msg(self) -> bytes:
        header = self._recv_exact(4)
        if header is None: return None
        (length,) = struct.unpack("!I", header)
        return self._recv_exact(length)

    def _recv_exact(self, n: int):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk: return None
            buf += chunk
        return buf

    def close(self):
        self.sock.close()
