"""
Poscure Settings Panel — tabbed settings dialog.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox,
    QSlider, QLineEdit, QScrollArea, QSizePolicy, QFrame,
    QKeySequenceEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence

from core.settings import get_settings
from widgets.shared import SectionLabel, HDivider, Card
from ui.theme import COLORS
from utils.hotkeys import HOTKEY_LABELS


def _row(label: str, widget: QWidget, note: str = "") -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(12)
    lbl = QLabel(label)
    lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; min-width: 160px; background: transparent;")
    lay.addWidget(lbl)
    lay.addWidget(widget, 1)
    if note:
        n = QLabel(note)
        n.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px; background: transparent;")
        lay.addWidget(n)
    return lay


class SettingsPanel(QDialog):
    settings_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._s = get_settings()
        self.setWindowTitle("Settings — Poscure")
        self.setMinimumSize(640, 520)
        self.setStyleSheet(f"background: {COLORS['bg_base']}; color: {COLORS['text_primary']};")
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        tbar = QWidget()
        tbar.setFixedHeight(52)
        tbar.setStyleSheet(f"background: {COLORS['bg_surface']}; border-bottom: 1px solid {COLORS['border_base']};")
        tlay = QHBoxLayout(tbar)
        tlay.setContentsMargins(20, 0, 20, 0)
        title = QLabel("Settings")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600;")
        tlay.addWidget(title)
        root.addWidget(tbar)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: {COLORS['bg_base']};
            }}
            QTabBar::tab {{
                background: transparent;
                color: {COLORS['text_secondary']};
                padding: 10px 20px;
                border: none;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {COLORS['text_primary']};
                border-bottom: 2px solid {COLORS['accent']};
            }}
            QTabBar::tab:hover {{
                color: {COLORS['text_primary']};
            }}
        """)

        self._tabs.addTab(self._build_general(),    "General")
        self._tabs.addTab(self._build_appearance(), "Appearance")
        self._tabs.addTab(self._build_session(),    "Session")
        self._tabs.addTab(self._build_hotkeys(),    "Hotkeys")
        self._tabs.addTab(self._build_performance(),"Performance")
        root.addWidget(self._tabs, 1)

        # Bottom buttons
        bbar = QWidget()
        bbar.setFixedHeight(56)
        bbar.setStyleSheet(f"background: {COLORS['bg_surface']}; border-top: 1px solid {COLORS['border_base']};")
        blay = QHBoxLayout(bbar)
        blay.setContentsMargins(20, 0, 20, 0)
        blay.setSpacing(10)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {COLORS['border_base']};
                color: {COLORS['text_secondary']};
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{ color: {COLORS['error']}; border-color: {COLORS['error']}; }}
        """)
        reset_btn.clicked.connect(self._on_reset)

        save_btn = QPushButton("Save & Close")
        save_btn.setFixedSize(140, 36)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #0A0A0B;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: #D9BA8F; }}
        """)
        save_btn.clicked.connect(self._on_save)

        blay.addWidget(reset_btn)
        blay.addStretch()
        blay.addWidget(save_btn)
        root.addWidget(bbar)

    def _scroll_tab(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setStyleSheet(f"background: {COLORS['bg_base']};")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)
        lay.addWidget(widget)
        lay.addStretch()
        scroll.setWidget(inner)
        return scroll

    # ── Tabs ──────────────────────────────────────────────────────────────────

    def _build_general(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        self._startup_max = QCheckBox("Start maximized")
        self._startup_max.setChecked(self._s.get("start_maximized", False))

        self._remember_folders = QCheckBox("Remember folders on startup")
        self._remember_folders.setChecked(self._s.get("remember_folders", True))

        self._auto_refresh = QCheckBox("Auto-refresh library on startup")
        self._auto_refresh.setChecked(self._s.get("auto_refresh_on_start", False))

        self._always_on_top = QCheckBox("Always on top during sessions")
        self._always_on_top.setChecked(self._s.get("always_on_top", False))

        for chk in [self._startup_max, self._remember_folders,
                    self._auto_refresh, self._always_on_top]:
            chk.setStyleSheet(f"color: {COLORS['text_secondary']};")
            lay.addWidget(chk)

        return self._scroll_tab(w)

    def _build_appearance(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        SectionLabel("Accent Color")

        self._accent_combo = QComboBox()
        accents = [
            ("Warm Gold",   "#C8A97E"),
            ("Soft Blue",   "#6B9FC8"),
            ("Sage Green",  "#6BA888"),
            ("Warm Rose",   "#C87878"),
            ("Muted Purple","#9B78C8"),
        ]
        for name, val in accents:
            self._accent_combo.addItem(name, val)
        cur = self._s.get("accent_color", "#C8A97E")
        for i, (_, v) in enumerate(accents):
            if v == cur:
                self._accent_combo.setCurrentIndex(i)

        lay.addLayout(_row("Accent color", self._accent_combo))

        self._thumb_quality = QComboBox()
        self._thumb_quality.addItems(["Low", "Medium", "High"])
        cur_q = self._s.get("thumbnail_quality", "medium").capitalize()
        self._thumb_quality.setCurrentText(cur_q)
        lay.addLayout(_row("Thumbnail quality", self._thumb_quality))

        self._thumb_cols = QSpinBox()
        self._thumb_cols.setRange(3, 8)
        self._thumb_cols.setValue(self._s.get("thumbnail_columns", 5))
        lay.addLayout(_row("Default grid columns", self._thumb_cols))

        self._fit_combo = QComboBox()
        self._fit_combo.addItem("Fit (letterbox)", "fit")
        self._fit_combo.addItem("Fill (crop)",     "fill")
        self._fit_combo.addItem("Original (1:1)",  "original")
        cur_fit = self._s.get("default_fit_mode", "fit")
        for i in range(self._fit_combo.count()):
            if self._fit_combo.itemData(i) == cur_fit:
                self._fit_combo.setCurrentIndex(i)
        lay.addLayout(_row("Default image fit", self._fit_combo))

        self._timer_pos = QComboBox()
        self._timer_pos.addItems(["Top Right", "Top Left", "Top Center"])
        pos_map = {"top-right": 0, "top-left": 1, "top-center": 2}
        self._timer_pos.setCurrentIndex(
            pos_map.get(self._s.get("timer_position", "top-right"), 0)
        )
        lay.addLayout(_row("Timer position", self._timer_pos))

        self._timer_size = QComboBox()
        self._timer_size.addItems(["Small", "Medium", "Large"])
        sz_map = {"small": 0, "medium": 1, "large": 2}
        self._timer_size.setCurrentIndex(
            sz_map.get(self._s.get("timer_size", "large"), 2)
        )
        lay.addLayout(_row("Timer size", self._timer_size))

        return self._scroll_tab(w)

    def _build_session(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        self._show_timer_chk = QCheckBox("Show timer during session")
        self._show_timer_chk.setChecked(self._s.get("show_timer", True))

        self._show_counter_chk = QCheckBox("Show image counter")
        self._show_counter_chk.setChecked(self._s.get("show_counter", True))

        self._show_progress_chk = QCheckBox("Show progress bar")
        self._show_progress_chk.setChecked(self._s.get("show_progress_bar", True))

        self._show_fname_chk = QCheckBox("Show filename in session")
        self._show_fname_chk.setChecked(self._s.get("show_filename", False))

        for chk in [self._show_timer_chk, self._show_counter_chk,
                    self._show_progress_chk, self._show_fname_chk]:
            chk.setStyleSheet(f"color: {COLORS['text_secondary']};")
            lay.addWidget(chk)

        return self._scroll_tab(w)

    def _build_hotkeys(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        note = QLabel("Click a field and press the key combination to change a shortcut.")
        note.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px; background: transparent;")
        note.setWordWrap(True)
        lay.addWidget(note)
        lay.addSpacing(6)

        self._hotkey_edits: dict[str, QKeySequenceEdit] = {}
        for action, label in HOTKEY_LABELS.items():
            edit = QKeySequenceEdit(QKeySequence(self._s.get_hotkey(action)))
            edit.setStyleSheet(f"""
                QKeySequenceEdit {{
                    background: {COLORS['bg_surface']};
                    border: 1px solid {COLORS['border_base']};
                    border-radius: 5px;
                    padding: 5px 8px;
                    color: {COLORS['text_primary']};
                }}
            """)
            self._hotkey_edits[action] = edit
            lay.addLayout(_row(label, edit))

        return self._scroll_tab(w)

    def _build_performance(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        self._preload_spin = QSpinBox()
        self._preload_spin.setRange(0, 10)
        self._preload_spin.setValue(self._s.get("preload_count", 3))
        lay.addLayout(_row("Preload next N images", self._preload_spin, "images"))

        self._max_mem_spin = QSpinBox()
        self._max_mem_spin.setRange(100, 2048)
        self._max_mem_spin.setSingleStep(50)
        self._max_mem_spin.setValue(self._s.get("max_memory_mb", 400))
        lay.addLayout(_row("Max cache memory", self._max_mem_spin, "MB"))

        self._cache_chk = QCheckBox("Cache thumbnails to disk (faster restarts)")
        self._cache_chk.setChecked(self._s.get("cache_thumbnails", True))
        self._cache_chk.setStyleSheet(f"color: {COLORS['text_secondary']};")
        lay.addWidget(self._cache_chk)

        return self._scroll_tab(w)

    # ── Save / reset ──────────────────────────────────────────────────────────

    def _on_save(self) -> None:
        s = self._s

        # General
        s.set("start_maximized",     self._startup_max.isChecked())
        s.set("remember_folders",    self._remember_folders.isChecked())
        s.set("auto_refresh_on_start", self._auto_refresh.isChecked())
        s.set("always_on_top",       self._always_on_top.isChecked())

        # Appearance
        s.set("accent_color",        self._accent_combo.currentData())
        s.set("thumbnail_quality",   self._thumb_quality.currentText().lower())
        s.set("thumbnail_columns",   self._thumb_cols.value())
        s.set("default_fit_mode",    self._fit_combo.currentData())
        pos_map = {0: "top-right", 1: "top-left", 2: "top-center"}
        s.set("timer_position",      pos_map[self._timer_pos.currentIndex()])
        sz_map = {0: "small", 1: "medium", 2: "large"}
        s.set("timer_size",          sz_map[self._timer_size.currentIndex()])

        # Session
        s.set("show_timer",          self._show_timer_chk.isChecked())
        s.set("show_counter",        self._show_counter_chk.isChecked())
        s.set("show_progress_bar",   self._show_progress_chk.isChecked())
        s.set("show_filename",       self._show_fname_chk.isChecked())

        # Hotkeys
        for action, edit in self._hotkey_edits.items():
            key_str = edit.keySequence().toString()
            s.set_hotkey(action, key_str)

        # Performance
        s.set("preload_count",       self._preload_spin.value())
        s.set("max_memory_mb",       self._max_mem_spin.value())
        s.set("cache_thumbnails",    self._cache_chk.isChecked())

        self.settings_changed.emit()
        self.accept()

    def _on_reset(self) -> None:
        self._s.reset_to_defaults()
        self.reject()
