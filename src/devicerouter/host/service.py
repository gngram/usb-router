import time
from typing import Dict, Any, Optional

from devicerouter.transports.vsock import VsockClient

class HostService:
    def __init__(self, schema: Dict[str, Any], guest_cid: int, guest_port: int, ack_delay: float = 0.0):
        # schema = {"devices":{...}, "current-mount":{...}}
        self.schema = schema
        self.client = VsockClient(
            guest_cid=guest_cid, guest_port=guest_port,
            on_message=self.on_msg, on_connect=self.on_connect, on_disconnect=self.on_disconnect
        )
        self.ack_delay = ack_delay
        self.connected = False

    def start(self):
        self.client.start()

    def stop(self):
        self.client.stop()

    def on_connect(self):
        self.connected = True
        print("[HOST] Connected to GUI VM")
        # Send snapshot as-is
        snap = {"type": "snapshot", "devices": self.schema["devices"], "current-mount": self.schema["current-mount"], "ts": time.time()}
        self.client.send(snap)
        print("[HOST] Sent snapshot containing", len(self.schema["devices"]), "devices.")

    def on_disconnect(self):
        if self.connected:
            print("[HOST] Disconnected; retrying…")
        self.connected = False

    def on_msg(self, msg: Dict[str, Any]):
        t = msg.get("type")
        if t in ("selection", "connect_change"):
            req_id = msg.get("request_id")
            device_id = msg.get("device_id")
            target_vm = msg.get("target_vm")
            dev_meta = self.schema["devices"].get(device_id, {})
            permitted = dev_meta.get("permitted_vms", [])
            ok = target_vm in permitted
            if self.ack_delay > 0:
                time.sleep(self.ack_delay)
            ack = {
                "type": "ack",
                "request_id": req_id,
                "status": "ok" if ok else "error",
                "message": "" if ok else f"Target '{target_vm}' not permitted for '{device_id}'",
                "ts": time.time()
            }
            self.client.send(ack)
            print(f"[HOST] {t} {device_id} -> {target_vm} :: {ack['status']}")
        else:
            print(f"[HOST] unknown msg: {msg}")

