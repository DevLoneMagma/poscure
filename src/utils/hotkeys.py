"""
Poscure Hotkeys — centralized hotkey registry.
Maps action names to QKeySequence strings and connects to callbacks.
"""

from __future__ import annotations
from typing import Callable, Optional

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


HOTKEY_LABELS = {
    "pause_resume":   "Pause / Resume",
    "next":           "Next Image",
    "previous":       "Previous Image",
    "fullscreen":     "Toggle Fullscreen",
    "grayscale":      "Toggle Grayscale",
    "mirror":         "Toggle Mirror",
    "toggle_timer":   "Toggle Timer Visibility",
    "end_session":    "End Session",
    "open_settings":  "Open Settings",
}


class HotkeyManager:
    """
    Registers QShortcut objects on a given widget.
    Shortcuts are re-registered whenever settings change.
    """

    def __init__(self, widget: QWidget, settings) -> None:
        self._widget   = widget
        self._settings = settings
        self._shortcuts: dict[str, QShortcut] = {}
        self._callbacks: dict[str, Callable]  = {}

    def register(self, action: str, callback: Callable) -> None:
        self._callbacks[action] = callback
        self._apply(action)

    def _apply(self, action: str) -> None:
        key_str = self._settings.get_hotkey(action)
        if not key_str:
            return

        # Remove old shortcut
        if action in self._shortcuts:
            self._shortcuts[action].setEnabled(False)
            self._shortcuts[action].deleteLater()

        seq = QKeySequence(key_str)
        sc  = QShortcut(seq, self._widget)
        sc.setContext(Qt.ShortcutContext.WindowShortcut)
        if action in self._callbacks:
            sc.activated.connect(self._callbacks[action])
        self._shortcuts[action] = sc

    def refresh_all(self) -> None:
        for action in list(self._callbacks.keys()):
            self._apply(action)

    def unregister_all(self) -> None:
        for sc in self._shortcuts.values():
            sc.setEnabled(False)
            sc.deleteLater()
        self._shortcuts.clear()

    def set_enabled(self, enabled: bool) -> None:
        for sc in self._shortcuts.values():
            sc.setEnabled(enabled)
