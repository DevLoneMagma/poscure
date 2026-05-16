"""
Poscure Main Window — root QMainWindow.
Controls navigation between Library → Session Config → Session.
"""

from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QSizePolicy,
    QApplication
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QIcon, QKeySequence, QShortcut

from core.library import ImageEntry, get_library
from core.session import SessionConfig
from core.settings import get_settings
from ui.theme import COLORS, build_stylesheet
from ui.library_view import LibraryView
from ui.session_config import SessionConfigView
from ui.session_window import SessionWindow
from ui.settings_panel import SettingsPanel
from ui.about_dialog import AboutDialog


# Page indices in QStackedWidget
PAGE_LIBRARY = 0
PAGE_CONFIG  = 1
PAGE_SESSION = 2


class TitleBar(QWidget):
    """Custom slim title bar with app name and nav buttons."""

    settings_clicked = None   # set by MainWindow

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setStyleSheet(f"""
            background: {COLORS['bg_surface']};
            border-bottom: 1px solid {COLORS['border_base']};
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 16, 0)
        lay.setSpacing(12)

        # Logo + name
        logo = QLabel("◈")
        logo.setStyleSheet(f"font-size: 18px; color: {COLORS['accent']}; background: transparent;")
        name = QLabel("Poscure")
        name.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 700;
            color: {COLORS['text_primary']};
            letter-spacing: 0.5px;
            background: transparent;
        """)
        lay.addWidget(logo)
        lay.addWidget(name)
        lay.addStretch()

        # Right nav buttons
        self._about_btn = self._nav_btn("About")
        self._settings_btn = self._nav_btn("⚙  Settings")

        lay.addWidget(self._about_btn)
        lay.addWidget(self._settings_btn)

    def _nav_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {COLORS['border_base']};
                color: {COLORS['text_secondary']};
                border-radius: 5px;
                font-size: 12px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_hover']};
                color: {COLORS['text_primary']};
                border-color: {COLORS['border_light']};
            }}
        """)
        return btn

    @property
    def about_btn(self) -> QPushButton:
        return self._about_btn

    @property
    def settings_btn(self) -> QPushButton:
        return self._settings_btn


class MainWindow(QMainWindow):
    """
    Root window. Owns the stacked widget and handles all navigation.
    Library → Config → Session → back.
    """

    def __init__(self) -> None:
        super().__init__()
        self._settings = get_settings()
        self._library  = get_library()
        self._current_images: list[ImageEntry] = []
        self._session_window: Optional[SessionWindow] = None

        self.setWindowTitle("Poscure")
        self.setMinimumSize(960, 640)

        # Apply global stylesheet
        accent = self._settings.get("accent_color", "#C8A97E")
        QApplication.instance().setStyleSheet(build_stylesheet(accent))

        self._build()
        self._restore_geometry()
        self._auto_refresh()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        vlay = QVBoxLayout(root)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        # Title bar
        self._title_bar = TitleBar()
        self._title_bar.about_btn.clicked.connect(self._open_about)
        self._title_bar.settings_btn.clicked.connect(self._open_settings)
        vlay.addWidget(self._title_bar)

        # Stacked pages
        self._stack = QStackedWidget()
        vlay.addWidget(self._stack, 1)

        # ── Library page ──
        self._library_view = LibraryView()
        self._library_view.start_session_requested.connect(self._on_session_requested)
        self._stack.addWidget(self._library_view)   # PAGE_LIBRARY = 0

        # Config and session pages are created on demand
        self._stack.addWidget(QWidget())   # placeholder PAGE_CONFIG  = 1
        self._stack.addWidget(QWidget())   # placeholder PAGE_SESSION = 2

        # Hotkey: Ctrl+S → settings
        sc = QShortcut(QKeySequence("Ctrl+S"), self)
        sc.activated.connect(self._open_settings)

        self._stack.setCurrentIndex(PAGE_LIBRARY)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_session_requested(self, images: list[ImageEntry]) -> None:
        """Called from LibraryView — go to config screen."""
        if not images:
            # Use all library images
            images = self._library.all_images()
        if not images:
            from widgets.shared import Toast
            Toast(self, "No images found. Add a folder first.", color=COLORS["error"])
            return

        self._current_images = images

        # Rebuild config page
        config_view = SessionConfigView(images)
        config_view.session_ready.connect(self._on_config_done)
        config_view.back_requested.connect(lambda: self._stack.setCurrentIndex(PAGE_LIBRARY))
        self._stack.removeWidget(self._stack.widget(PAGE_CONFIG))
        self._stack.insertWidget(PAGE_CONFIG, config_view)
        self._stack.setCurrentIndex(PAGE_CONFIG)
        self._title_bar.hide()

    def _on_config_done(self, config: SessionConfig) -> None:
        """Called from SessionConfigView — launch session."""
        self._title_bar.hide()

        # Create session window as a top-level fullscreen window
        # (not embedded in stack, so it can go truly fullscreen)
        if self._session_window:
            self._session_window.close()
            self._session_window.deleteLater()

        self._session_window = SessionWindow(config)
        self._session_window.session_ended.connect(self._on_session_ended)
        self._session_window.show()
        self.hide()

    def _on_session_ended(self) -> None:
        """Return to library after session ends."""
        if self._session_window:
            self._session_window.close()
            self._session_window = None

        self.show()
        self._title_bar.show()

        # Rebuild library placeholder
        self._stack.removeWidget(self._stack.widget(PAGE_CONFIG))
        self._stack.insertWidget(PAGE_CONFIG, QWidget())
        self._stack.setCurrentIndex(PAGE_LIBRARY)

    # ── Dialogs ───────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        dlg = SettingsPanel(self)
        dlg.settings_changed.connect(self._on_settings_changed)
        dlg.exec()

    def _open_about(self) -> None:
        AboutDialog(self).exec()

    def _on_settings_changed(self) -> None:
        accent = self._settings.get("accent_color", "#C8A97E")
        QApplication.instance().setStyleSheet(build_stylesheet(accent))

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _restore_geometry(self) -> None:
        geo = self._settings.get("window_geometry")
        if geo:
            try:
                from PySide6.QtCore import QByteArray
                self.restoreGeometry(QByteArray.fromBase64(geo.encode()))
            except Exception:
                pass
        if self._settings.get("start_maximized", False):
            self.showMaximized()

    def _auto_refresh(self) -> None:
        if self._settings.get("auto_refresh_on_start", False):
            QTimer.singleShot(500, self._library.scan_all)

    def closeEvent(self, e) -> None:
        # Save geometry
        try:
            geo_bytes = self.saveGeometry().toBase64().data().decode()
            self._settings.set("window_geometry", geo_bytes)
        except Exception:
            pass
        if self._session_window:
            self._session_window.close()
        super().closeEvent(e)
