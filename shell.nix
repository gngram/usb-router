{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = [
    pkgs.python311
    pkgs.python311Packages.pyqt5
    pkgs.python311Packages.virtualenv
    pkgs.qt5.qtwayland
    pkgs.python311Packages.setuptools
    pkgs.python311Packages.wheel
    pkgs.python311Packages.build
  ];
  shellHook = ''
    if [ ! -d .venv ]; then
      virtualenv .venv
      source .venv/bin/activate
    else
      source .venv/bin/activate
    fi
    echo "Welcome to your Python development environment."
    export QT_QPA_PLATFORM=wayland
    echo "Now you can:"
    echo "  pip install -e ."
    echo "  devicerouter-gui --test-file ./schema.json"
  '';
}

