import json, time
from typing import Dict, Any, Optional
from pathlib import Path

from PyQt5.QtCore import QTimer, QObject

from devicerouter.schema import normalize_schema

class FileTestTransport(QObject):
    """
    TEST MODE: uses your JSON file as source of truth.
    - On start and whenever file changes, emits a full {"type":"snapshot", ...}
    - send(selection/change) simulates instant "ok" ACKs (no write here).
    - sync_from_registry() writes the current GUI-connected state into "current-mount".
    """
    def __init__(self, path: Path,
                 emit_message, emit_connected, emit_disconnected, emit_ack):
        super().__init__()
        self.path = path
        self.emit_message = emit_message
        self.emit_connected = emit_connected
        self.emit_disconnected = emit_disconnected
        self.emit_ack = emit_ack
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._maybe_reload)
        self._last_mtime: Optional[float] = None
        self._suppress_until = 0.0

        if not self.path.exists():
            self._write_doc({"devices": {}, "current-mount": {}})
        self._emit_snapshot_from_file(initial=True)

    def start(self):
        self.timer.start()
        self.emit_connected()

    def stop(self):
        self.timer.stop()
        self.emit_disconnected()

    def send(self, obj: Dict[str, Any]):
        # Simulate immediate ACK ok
        t = obj.get("type")
        if t in ("selection", "connect_change"):
            self.emit_ack(obj.get("request_id",""), "ok", "")

    def sync_from_registry(self, reg_devices: Dict[str, Dict[str, Any]]):
        doc = self._read_doc()
        doc = normalize_schema(doc)
        mounts = {}
        for dev_id, info in reg_devices.items():
            mounts[dev_id] = info.get("connected_to") or info.get("selected")
        doc["current-mount"] = mounts
        self._write_doc(doc)

    # ---- helpers ----
    def _read_doc(self) -> Dict[str, Any]:
        try:
            return json.loads(self.path.read_text() or "{}")
        except Exception:
            return {}

    def _write_doc(self, doc: Dict[str, Any]):
        self.path.write_text(json.dumps(doc, indent=2))
        self._suppress_until = time.time() + 0.5
        try:
            self._last_mtime = self.path.stat().st_mtime
        except Exception:
            pass

    def _emit_snapshot_from_file(self, initial=False):
        doc = normalize_schema(self._read_doc())
        payload = {"type": "snapshot", "devices": doc["devices"], "current-mount": doc["current-mount"], "ts": time.time()}
        self.emit_message(payload)
        if initial:
            try:
                self._last_mtime = self.path.stat().st_mtime
            except Exception:
                pass

    def _maybe_reload(self):
        try:
            m = self.path.stat().st_mtime
        except FileNotFoundError:
            return
        if m == self._last_mtime or time.time() < self._suppress_until:
            return
        self._last_mtime = m
        self._emit_snapshot_from_file()

