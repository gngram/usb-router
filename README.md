# devicerouter

Host ↔ GUI-VM device routing over vsock with a PyQt5 GUI. Test mode lets you
develop without vsock by using a JSON file as the “transport”.

## Install (editable)
```bash
pip install -e ".[gui]"
```

On COSMIC/Wayland you may want:

```bash
export QT_QPA_PLATFORM=wayland
```

## Schema

```json
{
  "devices": {
    "1a86:7523": {
      "permitted_vms": ["vm-a","vm-b","vm-x"],
      "Vendor": "QinHeng",
      "Product": "CH340 Serial"
    }
  },
  "current-mount": {
    "1a86:7523": "vm-b"
  }
}

```

## Run (test mode):

```bash
$> devicerouter-gui --test-file ./schema.json --combo-width 260 --popup-width 320

```

## Run (vsock):

```
# Host:
devicerouter-host --schema-json ./schema.json --guest-cid 101 --guest-port 7000

# GUI VM:
devicerouter-gui --port 7000

```

### Notes

- The GUI renders each device as:
  **`Vendor (Product) [vid:pid]:`**  
  with a dropdown below (**Select** + permitted VMs).
- **Save** (in test mode) writes the current selections into `current-mount` in the JSON file.
- In **vsock mode**, the host sends a `snapshot` once connected and responds to `selection` / `connect_change` with an `ack`.
- Combo/popup widths can be set with `--combo-width` and `--popup-width`.



