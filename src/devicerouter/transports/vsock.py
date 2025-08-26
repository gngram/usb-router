import socket, time, threading
from typing import Callable, Dict, Any, Optional
from devicerouter.protocol import jsonl_reader, jsonl_send

AF_VSOCK = getattr(socket, "AF_VSOCK", None)
SOCK_STREAM = socket.SOCK_STREAM

class VsockServer(threading.Thread):
    """GUI-VM side: listens for a host connection."""
    def __init__(self, on_message: Callable[[Dict[str, Any]], None],
                 on_connect: Callable[[], None],
                 on_disconnect: Callable[[], None],
                 my_port: int):
        super().__init__(daemon=True)
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.my_port = my_port
        self.sock: Optional[socket.socket] = None
        self.client: Optional[socket.socket] = None
        self.stop_flag = threading.Event()

    def run(self):
        if AF_VSOCK is None:
            print("AF_VSOCK not available; need Linux kernel vsock support.")
            return
        while not self.stop_flag.is_set():
            try:
                self.sock = socket.socket(AF_VSOCK, SOCK_STREAM)
                self.sock.bind((socket.VMADDR_CID_ANY, self.my_port))
                self.sock.listen(1)
                self.sock.settimeout(1.0)
                while not self.stop_flag.is_set():
                    try:
                        self.client, _ = self.sock.accept()
                        self.on_connect()
                        for msg in jsonl_reader(self.client):
                            self.on_message(msg)
                    except socket.timeout:
                        continue
                    finally:
                        if self.client:
                            try: self.client.close()
                            except: pass
                            self.client = None
                            self.on_disconnect()
            except Exception as e:
                print(f"[GUI] Vsock server error: {e}")
                time.sleep(1.0)
            finally:
                if self.sock:
                    try: self.sock.close()
                    except: pass
                    self.sock = None

    def send(self, obj: Dict[str, Any]):
        if not self.client:
            raise RuntimeError("No host connected")
        jsonl_send(self.client, obj)

    def stop(self):
        self.stop_flag.set()
        try:
            if self.client: self.client.close()
        except: pass
        try:
            if self.sock: self.sock.close()
        except: pass


class VsockClient(threading.Thread):
    """Host side: connects to GUI-VM vsock server."""
    def __init__(self, guest_cid: int, guest_port: int,
                 on_message: Callable[[Dict[str, Any]], None],
                 on_connect: Callable[[], None],
                 on_disconnect: Callable[[], None]):
        super().__init__(daemon=True)
        self.guest_cid = guest_cid
        self.guest_port = guest_port
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.stop_flag = threading.Event()
        self.sock: Optional[socket.socket] = None
        self.lock = threading.Lock()

    def run(self):
        if AF_VSOCK is None:
            print("AF_VSOCK not available; need Linux kernel vsock support.")
            return
        while not self.stop_flag.is_set():
            try:
                s = socket.socket(AF_VSOCK, SOCK_STREAM)
                s.settimeout(3.0)
                s.connect((self.guest_cid, self.guest_port))
                s.settimeout(None)
                self.sock = s
                self.on_connect()
                for msg in jsonl_reader(s):
                    self.on_message(msg)
            except Exception:
                self.on_disconnect()
                time.sleep(1.0)
            finally:
                if self.sock:
                    try: self.sock.close()
                    except: pass
                    self.sock = None

    def send(self, obj: Dict[str, Any]):
        with self.lock:
            if not self.sock:
                raise RuntimeError("Not connected to GUI VM")
            jsonl_send(self.sock, obj)

    def stop(self):
        self.stop_flag.set()
        if self.sock:
            try: self.sock.close()
            except: pass

