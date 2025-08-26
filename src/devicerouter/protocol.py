import json
import socket
from typing import Dict, Any, Generator

def jsonl_send(sock: socket.socket, obj: Dict[str, Any]) -> None:
    data = (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")
    sock.sendall(data)

def jsonl_reader(sock: socket.socket) -> Generator[Dict[str, Any], None, None]:
    buf = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            line = line.strip()
            if line:
                yield json.loads(line.decode("utf-8"))

# Message types (documentation)
# - snapshot: {"type":"snapshot","devices":{...},"current-mount":{...}}
# - selection: {"type":"selection","request_id":"...","device_id":"vid:pid","target_vm":"..."}
# - connect_change: same as selection but for changes
# - ack: {"type":"ack","request_id":"...","status":"ok"|"error","message":"", ...}
# - device_removed: {"type":"device_removed","device_id":"vid:pid"}

