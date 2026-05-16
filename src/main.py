"""
Poscure — entry point.
References. Flow. No distractions.
"""

from __future__ import annotations
import sys
import os

# ── Path setup (works both as script and frozen exe) ──────────────────────────
if getattr(sys, "frozen", False):
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _base)

# ── Qt environment ────────────────────────────────────────────────────────────
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QFont, QFontDatabase

from ui.main_window import MainWindow


def main() -> None:
    QCoreApplication.setApplicationName("Poscure")
    QCoreApplication.setOrganizationName("LoneMagma")
    QCoreApplication.setOrganizationDomain("poscure.vercel.app")
    QCoreApplication.setApplicationVersion("1.0.0")

    app = QApplication(sys.argv)

    # Font — Segoe UI on Windows, system sans-serif on Linux/macOS
    if sys.platform == "win32":
        font = QFont("Segoe UI", 10)
    else:
        font = QFont()
        font.setPointSize(10)
        font.setFamily("sans-serif")
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
