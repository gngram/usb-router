from functools import partial
from typing import Dict, Any, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QLabel, QComboBox, QVBoxLayout, QFrame
)

SELECT_LABEL = "Select"

def device_title_html(device_id: str, vendor: str, product: str) -> str:
    # Bold: Vendor (Product) [vid:pid]:
    v = vendor or ""
    p = product or ""
    return f"<b>{v} ({p}) [{device_id}]:</b>"

def make_combo(device_id: str, targets: List[str], selected: Optional[str],
               on_change, combo_width: Optional[int] = None, popup_width: Optional[int] = None) -> QComboBox:
    combo = QComboBox()
    combo.setEditable(False)
    items = [SELECT_LABEL] + targets
    combo.addItems(items)

    # Combo (widget) width
    if combo_width:
        combo.setFixedWidth(combo_width)
    else:
        combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        combo.setMinimumContentsLength(max((len(s) for s in items), default=8))

    # Popup (dropdown) width
    if popup_width:
        combo.view().setMinimumWidth(popup_width)
    else:
        fm = combo.fontMetrics()
        longest_px = max((fm.horizontalAdvance(s) for s in items), default=80)
        combo.view().setMinimumWidth(longest_px + 60)

    current = 0 if not selected or selected not in targets else (targets.index(selected) + 1)
    combo.setCurrentIndex(current)
    combo.currentIndexChanged.connect(partial(on_change, device_id))
    return combo

def make_device_block(device_id: str, info: Dict[str, Any],
                      on_change, combo_width: Optional[int], popup_width: Optional[int]) -> QFrame:
    container = QFrame()
    container.setFrameShape(QFrame.NoFrame)
    v = QVBoxLayout(container)
    v.setSpacing(6)

    lbl = QLabel()
    lbl.setTextFormat(Qt.RichText)
    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    lbl.setText(device_title_html(device_id, info.get("vendor",""), info.get("product","")))
    v.addWidget(lbl)

    combo = make_combo(device_id, info.get("targets", []), info.get("selected"),
                       on_change=on_change, combo_width=combo_width, popup_width=popup_width)
    v.addWidget(combo)

    container._label = lbl
    container._combo = combo
    return container

