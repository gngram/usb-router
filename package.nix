pyPkgs.buildPythonApplication {
  pname = "devicerouter";
  version = "0.1.0";
  src = ./.;
  pyproject = true;                     # use pyproject/PEP 517 build

  nativeBuildInputs = [
    pyPkgs.setuptools
    pyPkgs.wheel
    pkgs.wrapQtAppsHook
  ];

  propagatedBuildInputs = [
    pyPkgs.pyqt5                       # runtime deps: declare here, not in TOML
  ];

  buildInputs = [ pkgs.qt5.qtwayland ]; # non-Python libs for runtime
}

