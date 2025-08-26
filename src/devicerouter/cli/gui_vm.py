import argparse, json, os, sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from devicerouter.gui.app_qt5 import App

DEFAULT_LISTEN_PORT = 7000

def build_parser():
    p = argparse.ArgumentParser(description="GUI VM selector (PyQt5)")
    p.add_argument("--port", type=int, default=DEFAULT_LISTEN_PORT, help="vsock listen port")
    p.add_argument("--test-file", type=str, help="TEST MODE: use this JSON file as transport")
    p.add_argument("--combo-width", type=int, help="Fixed width of the combo widget (px)")
    p.add_argument("--popup-width", type=int, help="Minimum width of the dropdown list popup (px)")
    return p

def main():
    args = build_parser().parse_args()
    app = QApplication(sys.argv)

    use_file = bool(args.test_file)
    test_path = Path(args.test_file) if args.test_file else None
    if use_file and not test_path.exists():
        test_path.write_text(json.dumps({"devices": {}, "current-mount": {}}, indent=2))

    w = App(
        use_file_transport=use_file,
        my_port=args.port,
        test_file=test_path,
        combo_width=args.combo_width,
        popup_width=args.popup_width
    )
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

