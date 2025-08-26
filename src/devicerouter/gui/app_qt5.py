import uuid, time
from pathlib import Path
from typing import Dict, Any, Optional

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QScrollArea
)

from devicerouter.gui.registry import Registry
from devicerouter.gui.widgets import make_device_block, SELECT_LABEL
from devicerouter.transports.vsock import VsockServer
from devicerouter.transports.filetest import FileTestTransport

ACK_TIMEOUT_MS = 6000

class App(QWidget):
    def __init__(self, use_file_transport: bool, my_port: int,
                 test_file: Optional[Path], combo_width: Optional[int], popup_width: Optional[int]):
        super().__init__()
        self.setWindowTitle("Device Router (GUI VM - Qt5)")
        self.resize(760, 560)

        # State
        self.registry = Registry()
        self.pending: Dict[str, Dict[str, Any]] = {}
        self.host_connected = False
        self.combo_width = combo_width
        self.popup_width = popup_width

        # device_id -> widgets
        self.block_by_device: Dict[str, QWidget] = {}
        self.combo_by_device: Dict[str, QWidget] = {}

        # --------- UI ---------
        root = QVBoxLayout(self)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.devices_layout = QVBoxLayout(self.inner)
        self.devices_layout.setSpacing(12)
        self.devices_layout.addStretch(1)
        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll)

        status_row = QHBoxLayout()
        self.status_lbl = QLabel("Status: initializing…")
        status_row.addWidget(self.status_lbl)
        status_row.addStretch(1)
        hint = QLabel(("TEST MODE (file) — " if use_file_transport else "VSOCK MODE — ") +
                      f"First dropdown item is “{SELECT_LABEL}”.")
        hint.setStyleSheet("color: gray;")
        status_row.addWidget(hint)
        root.addLayout(status_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.save_btn = QPushButton("Save")
        self.save_btn.setToolTip("In test mode: write selections to JSON. In vsock mode: no-op.")
        self.save_btn.clicked.connect(self.on_save_clicked)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.close_btn)
        root.addLayout(btn_row)

        # Transport wiring
        if use_file_transport:
            self.transport = FileTestTransport(
                path=test_file,
                emit_message=self.on_msg,
                emit_connected=self.on_connected,
                emit_disconnected=self.on_disconnected,
                emit_ack=self.on_ack
            )
            self.transport.start()
        else:
            self.transport = VsockServer(
                on_message=self.on_msg,
                on_connect=self.on_connected,
                on_disconnect=self.on_disconnected,
                my_port=my_port
            )
            self.transport.start()

    # ---------- building / updating blocks ----------
    def _add_or_update_block(self, device_id: str, info: Dict[str, Any]):
        container = self.block_by_device.get(device_id)
        if container is None:
            container = make_device_block(
                device_id, info,
                on_change=self.on_combo_changed,
                combo_width=self.combo_width,
                popup_width=self.popup_width
            )
            # Insert above the final stretch
            self.devices_layout.insertWidget(self.devices_layout.count()-1, container)
            self.block_by_device[device_id] = container
            self.combo_by_device[device_id] = container._combo
        else:
            # Update title and combo items
            lbl = getattr(container, "_label", None)
            if lbl:
                from devicerouter.gui.widgets import device_title_html
                lbl.setText(device_title_html(device_id, info.get("vendor",""), info.get("product","")))
            combo = getattr(container, "_combo", None)
            if combo:
                combo.blockSignals(True)
                items = [SELECT_LABEL] + info.get("targets", [])
                combo.clear()
                combo.addItems(items)
                sel = info.get("selected")
                idx = 0 if not sel or sel not in info.get("targets", []) else (info["targets"].index(sel) + 1)
                combo.setCurrentIndex(idx)
                combo.blockSignals(False)

    def _remove_block(self, device_id: str):
        w = self.block_by_device.pop(device_id, None)
        self.combo_by_device.pop(device_id, None)
        if w:
            w.setParent(None)
            w.deleteLater()

    # ---------- helpers ----------
    def _is_device_pending(self, device_id: str) -> bool:
        return any(p.get("device_id") == device_id for p in self.pending.values())

    def _set_combo_choice(self, device_id: str, choice: Optional[str]):
        combo = self.combo_by_device.get(device_id)
        info = self.registry.devices.get(device_id, {})
        targets = info.get("targets", [])
        idx = 0 if not choice or choice not in targets else (targets.index(choice) + 1)
        if combo:
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    # ---------- transport events ----------
    def on_connected(self):
        self.host_connected = True
        self.status_lbl.setText("Status: connected")

    def on_disconnected(self):
        self.host_connected = False
        self.status_lbl.setText("Status: disconnected / waiting")

    def on_msg(self, msg: Dict[str, Any]):
        if msg.get("type") == "snapshot":
            devices = msg.get("devices", {}) or {}
            mounts = msg.get("current-mount", {}) or {}

            # remove missing
            current_ids = set(self.registry.devices.keys())
            new_ids = set(devices.keys())
            for rem_id in (current_ids - new_ids):
                self._remove_block(rem_id)
                self.registry.devices.pop(rem_id, None)

            # add/update
            for dev_id, meta in devices.items():
                permitted = list(meta.get("permitted_vms", []))
                vendor = meta.get("Vendor") or ""
                product = meta.get("Product") or ""
                selected = mounts.get(dev_id)
                self.registry.devices[dev_id] = {
                    "targets": permitted,
                    "selected": selected,
                    "connected_to": selected,
                    "vendor": vendor,
                    "product": product,
                }
                self._add_or_update_block(dev_id, self.registry.devices[dev_id])

        elif msg.get("type") == "ack":
            self.on_ack(msg.get("request_id",""), msg.get("status","error"), msg.get("message",""))

    def _start_pending(self, device_id: str, request_id: str, prev_choice: Optional[str], simulate_immediate_ok: bool):
        combo = self.combo_by_device.get(device_id)
        if simulate_immediate_ok:
            self.on_ack(request_id, "ok", "")
            return
        if combo:
            combo.setEnabled(False)
        timer = QTimer(self)
        timer.setSingleShot(True)
        def on_to():
            if combo:
                combo.setEnabled(True)
            QMessageBox.critical(self, "Timeout", f"{device_id}: no ACK from host")
            self.registry.devices[device_id]["selected"] = prev_choice
            self._set_combo_choice(device_id, prev_choice)
            self.pending.pop(request_id, None)
        timer.timeout.connect(on_to)
        timer.start(ACK_TIMEOUT_MS)
        self.pending[request_id] = {"device_id": device_id, "timer": timer, "prev_choice": prev_choice}

    def send_selection_or_change(self, device_id: str, target_vm: str, kind: str):
        prev = self.registry.devices[device_id].get("connected_to")
        req = str(uuid.uuid4())
        self.registry.devices[device_id]["selected"] = target_vm
        simulate = hasattr(self.transport, "sync_from_registry")  # FileTestTransport has this
        self._start_pending(device_id, req, prev, simulate)
        try:
            self.transport.send({
                "type": "selection" if kind == "select" else "connect_change",
                "request_id": req,
                "device_id": device_id,
                "target_vm": target_vm,
                "ts": time.time()
            })
            if simulate:  # test mode—apply immediately
                self.registry.devices[device_id]["connected_to"] = target_vm
        except Exception as e:
            QMessageBox.critical(self, "Send error", f"Failed to send: {e}")

    def on_ack(self, request_id: str, status: str, message: str):
        p = self.pending.pop(request_id, None)
        if not p:
            return
        device_id = p["device_id"]
        if p.get("timer"):
            p["timer"].stop()
        combo = self.combo_by_device.get(device_id)
        if combo:
            combo.setEnabled(True)
        if status == "ok":
            sel = self.registry.devices[device_id].get("selected")
            self.registry.devices[device_id]["connected_to"] = sel
        else:
            prev = p.get("prev_choice")
            self.registry.devices[device_id]["selected"] = prev
            self._set_combo_choice(device_id, prev)
            QMessageBox.critical(self, "Host error", f"{device_id}: {message or 'error'}")

    # ---------- UI events ----------
    def on_combo_changed(self, device_id: str, _index: int):
        if self._is_device_pending(device_id):
            info = self.registry.devices.get(device_id, {})
            self._set_combo_choice(device_id, info.get("selected"))
            QMessageBox.information(self, "Please wait", f"{device_id}: request already pending.")
            return
        combo = self.combo_by_device.get(device_id)
        if not combo:
            return
        choice = combo.currentText()
        if choice == SELECT_LABEL:
            self.registry.devices[device_id]["selected"] = None
            return
        info = self.registry.devices.get(device_id, {})
        connected = info.get("connected_to")
        if connected and connected != choice:
            self.send_selection_or_change(device_id, choice, kind="change")
        elif not connected:
            self.send_selection_or_change(device_id, choice, kind="select")
        else:
            self.registry.devices[device_id]["selected"] = choice

    def on_save_clicked(self):
        # Only meaningful in test mode
        if hasattr(self.transport, "sync_from_registry"):
            self.transport.sync_from_registry(self.registry.devices)
            QMessageBox.information(self, "Saved", "Selections written to JSON file.")
        else:
            QMessageBox.information(self, "Info", "No local file to save in vsock mode.")

