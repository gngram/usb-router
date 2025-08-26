from typing import Dict, Any, Optional

class Registry:
    """
    device_id (vid:pid) -> {
        'targets': [str,...],        # permitted_vms
        'selected': Optional[str],   # current UI selection (may be pending)
        'connected_to': Optional[str], # last ACKed connection
        'vendor': Optional[str],
        'product': Optional[str],
    }
    """
    def __init__(self):
        self.devices: Dict[str, Dict[str, Any]] = {}

    def clear(self):
        self.devices.clear()

