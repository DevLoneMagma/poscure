"""
Poscure Session Config Screen — pre-session setup with presets.
"""

from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QComboBox, QCheckBox, QRadioButton, QButtonGroup,
    QScrollArea, QFrame, QSizePolicy, QSpacerItem, QSlider,
    QGroupBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from core.library import ImageEntry
from core.session import SessionConfig, OrderMode
from core.settings import get_settings
from widgets.shared import Card, HDivider, SectionLabel, StatTile, ToggleButton
from ui.theme import COLORS


# ── Preset definitions ────────────────────────────────────────────────────────

PRESETS = [
    {"label": "30s Gestures",  "duration": 30,  "order": "random",       "random_dur": False},
    {"label": "60s Gestures",  "duration": 60,  "order": "random",       "random_dur": False},
    {"label": "2min Studies",  "duration": 120, "order": "random",       "random_dur": False},
    {"label": "5min Studies",  "duration": 300, "order": "sequential",   "random_dur": False},
    {"label": "Quick Mix",     "duration": 0,   "order": "random",       "random_dur": True,
     "dur_min": 15, "dur_max": 60},
]


# ── Section container ─────────────────────────────────────────────────────────

class Section(QFrame):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border_base']};
                border-radius: 10px;
            }}
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(14)

        if title:
            lbl = QLabel(title.upper())
            lbl.setStyleSheet(f"""
                color: {COLORS['text_tertiary']};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.5px;
                background: transparent;
                border: none;
            """)
            outer.addWidget(lbl)
            div = QFrame()
            div.setFixedHeight(1)
            div.setStyleSheet(f"background: {COLORS['border_base']}; border: none;")
            outer.addWidget(div)

        self.content = QVBoxLayout()
        self.content.setSpacing(12)
        outer.addLayout(self.content)


def _row(label_text: str, widget: QWidget, note: str = "") -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(12)
    lbl = QLabel(label_text)
    lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; background: transparent; border: none;")
    lbl.setMinimumWidth(130)
    lay.addWidget(lbl)
    lay.addWidget(widget, 1)
    if note:
        n = QLabel(note)
        n.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px; background: transparent; border: none;")
        lay.addWidget(n)
    return lay


# ── Session Config Widget ─────────────────────────────────────────────────────

class SessionConfigView(QWidget):
    """
    Full-featured pre-session configuration screen.
    Emits session_ready(config) when Start is clicked.
    """

    session_ready  = Signal(object)   # SessionConfig
    back_requested = Signal()

    def __init__(self, images: list[ImageEntry], parent=None) -> None:
        super().__init__(parent)
        self._images   = images
        self._settings = get_settings()
        self._build()
        self._load_last()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = QWidget()
        topbar.setFixedHeight(56)
        topbar.setStyleSheet(f"background: {COLORS['bg_surface']}; border-bottom: 1px solid {COLORS['border_base']};")
        tlay = QHBoxLayout(topbar)
        tlay.setContentsMargins(20, 0, 20, 0)

        back_btn = QPushButton("← Library")
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLORS['text_secondary']};
                font-size: 13px;
            }}
            QPushButton:hover {{ color: {COLORS['text_primary']}; }}
        """)
        back_btn.clicked.connect(self.back_requested)

        title = QLabel("Session Setup")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {COLORS['text_primary']};")

        self._img_count_lbl = QLabel(f"{len(self._images):,} images available")
        self._img_count_lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")

        tlay.addWidget(back_btn)
        tlay.addSpacing(20)
        tlay.addWidget(title)
        tlay.addStretch()
        tlay.addWidget(self._img_count_lbl)
        root.addWidget(topbar)

        # ── Scrollable body ───────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setStyleSheet(f"background: {COLORS['bg_base']};")
        blay = QVBoxLayout(body)
        blay.setContentsMargins(32, 24, 32, 32)
        blay.setSpacing(16)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        # ── Presets row ───────────────────────────────────────────────────────
        preset_sec = Section("Quick Presets")
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        self._preset_btns: list[QPushButton] = []
        for p in PRESETS:
            btn = QPushButton(p["label"])
            btn.setFixedHeight(34)
            btn.setCheckable(True)
            btn.setStyleSheet(self._preset_style(False))
            btn.clicked.connect(lambda checked, preset=p: self._apply_preset(preset))
            self._preset_btns.append(btn)
            preset_row.addWidget(btn)
        preset_row.addStretch()
        preset_sec.content.addLayout(preset_row)
        blay.addWidget(preset_sec)

        # ── Duration section ──────────────────────────────────────────────────
        dur_sec = Section("Timing")

        # Fixed vs random toggle
        mode_row = QHBoxLayout()
        self._fixed_rb  = QRadioButton("Fixed duration")
        self._random_rb = QRadioButton("Random range")
        self._fixed_rb.setChecked(True)
        self._fixed_rb.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self._random_rb.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self._dur_group = QButtonGroup(self)
        self._dur_group.addButton(self._fixed_rb, 0)
        self._dur_group.addButton(self._random_rb, 1)
        self._fixed_rb.toggled.connect(self._on_duration_mode)
        mode_row.addWidget(self._fixed_rb)
        mode_row.addSpacing(20)
        mode_row.addWidget(self._random_rb)
        mode_row.addStretch()
        dur_sec.content.addLayout(mode_row)

        # Fixed duration spin
        self._dur_spin = QSpinBox()
        self._dur_spin.setRange(5, 600)
        self._dur_spin.setValue(30)
        self._dur_spin.setSuffix(" sec")
        self._dur_spin.setFixedWidth(110)
        self._fixed_row = _row("Duration per image", self._dur_spin)
        dur_sec.content.addLayout(self._fixed_row)

        # Random range
        rng_widget = QWidget()
        rng_widget.setStyleSheet("background: transparent; border: none;")
        rng_lay = QHBoxLayout(rng_widget)
        rng_lay.setContentsMargins(0, 0, 0, 0)
        rng_lay.setSpacing(8)
        self._dur_min_spin = QSpinBox()
        self._dur_min_spin.setRange(5, 590)
        self._dur_min_spin.setValue(10)
        self._dur_min_spin.setSuffix(" sec")
        self._dur_min_spin.setFixedWidth(100)
        self._dur_max_spin = QSpinBox()
        self._dur_max_spin.setRange(6, 600)
        self._dur_max_spin.setValue(45)
        self._dur_max_spin.setSuffix(" sec")
        self._dur_max_spin.setFixedWidth(100)
        dash = QLabel("to")
        dash.setStyleSheet(f"color: {COLORS['text_tertiary']}; background: transparent; border: none;")
        rng_lay.addWidget(self._dur_min_spin)
        rng_lay.addWidget(dash)
        rng_lay.addWidget(self._dur_max_spin)
        rng_lay.addStretch()
        self._random_row = _row("Duration range", rng_widget)
        dur_sec.content.addLayout(self._random_row)
        self._toggle_duration_mode(fixed=True)
        blay.addWidget(dur_sec)

        # ── Images section ────────────────────────────────────────────────────
        img_sec = Section("Images")

        self._count_combo = QComboBox()
        self._count_combo.addItem("All images", "all")
        for n in [10, 20, 30, 50, 75, 100, 150, 200]:
            self._count_combo.addItem(str(n), n)
        self._count_combo.setFixedWidth(140)
        img_sec.content.addLayout(_row("Number of images", self._count_combo))

        self._order_combo = QComboBox()
        self._order_combo.addItem("Random",       "random")
        self._order_combo.addItem("Sequential",   "sequential")
        self._order_combo.addItem("Shuffle once", "shuffle_once")
        self._order_combo.setFixedWidth(140)
        img_sec.content.addLayout(_row("Order", self._order_combo))

        self._fit_combo = QComboBox()
        self._fit_combo.addItem("Fit (letterbox)", "fit")
        self._fit_combo.addItem("Fill (crop)",     "fill")
        self._fit_combo.addItem("Original (1:1)",  "original")
        self._fit_combo.setFixedWidth(160)
        img_sec.content.addLayout(_row("Image fit", self._fit_combo))

        blay.addWidget(img_sec)

        # ── Breaks section ────────────────────────────────────────────────────
        break_sec = Section("Breaks")

        self._break_chk = QCheckBox("Insert breaks during session")
        self._break_chk.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self._break_chk.toggled.connect(self._on_break_toggle)
        break_sec.content.addWidget(self._break_chk)

        self._break_every_spin = QSpinBox()
        self._break_every_spin.setRange(2, 100)
        self._break_every_spin.setValue(10)
        self._break_every_spin.setSuffix(" images")
        self._break_every_spin.setFixedWidth(120)
        self._break_every_row = _row("Break every", self._break_every_spin)

        self._break_dur_spin = QSpinBox()
        self._break_dur_spin.setRange(5, 300)
        self._break_dur_spin.setValue(30)
        self._break_dur_spin.setSuffix(" sec")
        self._break_dur_spin.setFixedWidth(120)
        self._break_dur_row = _row("Break duration", self._break_dur_spin)

        break_sec.content.addLayout(self._break_every_row)
        break_sec.content.addLayout(self._break_dur_row)
        self._set_break_rows_visible(False)
        blay.addWidget(break_sec)

        # ── Session options ───────────────────────────────────────────────────
        opt_sec = Section("Session Options")

        self._repeat_chk = QCheckBox("Repeat session when finished")
        self._repeat_chk.setStyleSheet(f"color: {COLORS['text_secondary']};")

        self._limit_chk = QCheckBox("Total session time limit")
        self._limit_chk.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self._limit_chk.toggled.connect(self._on_limit_toggle)

        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(1, 480)
        self._limit_spin.setValue(30)
        self._limit_spin.setSuffix(" min")
        self._limit_spin.setFixedWidth(110)
        self._limit_spin.setEnabled(False)
        self._limit_row = _row("Time limit", self._limit_spin)

        opt_sec.content.addWidget(self._repeat_chk)
        opt_sec.content.addWidget(self._limit_chk)
        opt_sec.content.addLayout(self._limit_row)
        blay.addWidget(opt_sec)

        blay.addStretch()

        # ── Bottom start bar ──────────────────────────────────────────────────
        startbar = QWidget()
        startbar.setFixedHeight(72)
        startbar.setStyleSheet(f"background: {COLORS['bg_surface']}; border-top: 1px solid {COLORS['border_base']};")
        slay = QHBoxLayout(startbar)
        slay.setContentsMargins(32, 0, 32, 0)
        slay.setSpacing(16)

        # Summary label
        self._summary_lbl = QLabel()
        self._summary_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        self._update_summary()

        start_btn = QPushButton("▶   Start Session")
        start_btn.setFixedSize(180, 44)
        start_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #0A0A0B;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{ background: #D9BA8F; }}
            QPushButton:pressed {{ background: {COLORS['accent_dim']}; color: {COLORS['text_primary']}; }}
        """)
        start_btn.clicked.connect(self._on_start)

        slay.addWidget(self._summary_lbl, 1)
        slay.addWidget(start_btn)
        root.addWidget(startbar)

        # Connect all controls to summary updater
        for w in [self._dur_spin, self._dur_min_spin, self._dur_max_spin,
                  self._count_combo, self._order_combo]:
            if hasattr(w, "valueChanged"):
                w.valueChanged.connect(self._update_summary)
            elif hasattr(w, "currentIndexChanged"):
                w.currentIndexChanged.connect(self._update_summary)
        self._fixed_rb.toggled.connect(self._update_summary)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _preset_style(self, active: bool) -> str:
        if active:
            return f"""
                QPushButton {{
                    background: {COLORS['accent']};
                    color: #0A0A0B;
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 0 14px;
                }}
            """
        return f"""
            QPushButton {{
                background: {COLORS['bg_elevated']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border_base']};
                border-radius: 6px;
                font-size: 12px;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_hover']};
                color: {COLORS['text_primary']};
                border-color: {COLORS['border_light']};
            }}
        """

    def _apply_preset(self, preset: dict) -> None:
        # Highlight active preset button
        for btn, p in zip(self._preset_btns, PRESETS):
            btn.setStyleSheet(self._preset_style(p is preset))

        if preset.get("random_dur"):
            self._random_rb.setChecked(True)
            self._dur_min_spin.setValue(preset.get("dur_min", 10))
            self._dur_max_spin.setValue(preset.get("dur_max", 60))
        else:
            self._fixed_rb.setChecked(True)
            self._dur_spin.setValue(preset["duration"])

        order_map = {"random": 0, "sequential": 1, "shuffle_once": 2}
        self._order_combo.setCurrentIndex(order_map.get(preset.get("order", "random"), 0))
        self._update_summary()

    def _on_duration_mode(self) -> None:
        self._toggle_duration_mode(self._fixed_rb.isChecked())

    def _toggle_duration_mode(self, fixed: bool) -> None:
        def _set_row_visible(lay: QHBoxLayout, visible: bool) -> None:
            for i in range(lay.count()):
                item = lay.itemAt(i)
                if item and item.widget():
                    item.widget().setVisible(visible)

        _set_row_visible(self._fixed_row, fixed)
        _set_row_visible(self._random_row, not fixed)

    def _on_break_toggle(self, checked: bool) -> None:
        self._set_break_rows_visible(checked)

    def _set_break_rows_visible(self, v: bool) -> None:
        def _set_row_visible(lay: QHBoxLayout, visible: bool) -> None:
            for i in range(lay.count()):
                item = lay.itemAt(i)
                if item and item.widget():
                    item.widget().setVisible(visible)
        _set_row_visible(self._break_every_row, v)
        _set_row_visible(self._break_dur_row, v)

    def _on_limit_toggle(self, checked: bool) -> None:
        self._limit_spin.setEnabled(checked)

    def _update_summary(self) -> None:
        total = len(self._images)
        count_data = self._count_combo.currentData()
        n = total if count_data == "all" else min(int(count_data), total)

        if self._fixed_rb.isChecked():
            d = self._dur_spin.value()
            est = n * d
        else:
            avg = (self._dur_min_spin.value() + self._dur_max_spin.value()) / 2
            est = int(n * avg)

        mins = est // 60
        secs = est % 60
        time_str = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
        self._summary_lbl.setText(f"{n} images  ·  ~{time_str} total")

    def _load_last(self) -> None:
        last = self._settings.get("last_session_config", {})
        if not last:
            return
        try:
            if last.get("duration_random"):
                self._random_rb.setChecked(True)
                self._dur_min_spin.setValue(last.get("duration_min", 10))
                self._dur_max_spin.setValue(last.get("duration_max", 45))
            else:
                self._fixed_rb.setChecked(True)
                self._dur_spin.setValue(last.get("duration", 30))

            order_map = {"random": 0, "sequential": 1, "shuffle_once": 2}
            self._order_combo.setCurrentIndex(
                order_map.get(last.get("order", "random"), 0)
            )
            self._repeat_chk.setChecked(last.get("repeat", False))
            self._break_chk.setChecked(last.get("break_enabled", False))
            self._break_every_spin.setValue(last.get("break_every_n", 10))
            self._break_dur_spin.setValue(last.get("break_duration", 30))
        except Exception:
            pass

    def _save_last(self) -> None:
        self._settings.set("last_session_config", {
            "duration": self._dur_spin.value(),
            "duration_random": self._random_rb.isChecked(),
            "duration_min": self._dur_min_spin.value(),
            "duration_max": self._dur_max_spin.value(),
            "order": self._order_combo.currentData(),
            "repeat": self._repeat_chk.isChecked(),
            "break_enabled": self._break_chk.isChecked(),
            "break_every_n": self._break_every_spin.value(),
            "break_duration": self._break_dur_spin.value(),
        })

    def _on_start(self) -> None:
        self._save_last()

        count_data = self._count_combo.currentData()
        image_count = "all" if count_data == "all" else int(count_data)

        order_str = self._order_combo.currentData()
        order_map = {
            "random":       OrderMode.RANDOM,
            "sequential":   OrderMode.SEQUENTIAL,
            "shuffle_once": OrderMode.SHUFFLE_ONCE,
        }

        config = SessionConfig(
            images         = self._images,
            duration       = self._dur_spin.value(),
            duration_random= self._random_rb.isChecked(),
            duration_min   = self._dur_min_spin.value(),
            duration_max   = self._dur_max_spin.value(),
            order          = order_map.get(order_str, OrderMode.RANDOM),
            image_count    = image_count,
            break_enabled  = self._break_chk.isChecked(),
            break_every_n  = self._break_every_spin.value(),
            break_duration = self._break_dur_spin.value(),
            repeat         = self._repeat_chk.isChecked(),
            time_limit     = (self._limit_spin.value() * 60
                              if self._limit_chk.isChecked() else 0),
        )
        self.session_ready.emit(config)
