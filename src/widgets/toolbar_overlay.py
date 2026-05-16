"""
Poscure Toolbar Overlay — floating minimal toolbar that auto-hides.
Appears on mouse movement, fades out after inactivity.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QProgressBar, QSizePolicy, QGraphicsOpacityEffect
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
)
from PySide6.QtGui import QColor, QPainter, QBrush, QPaintEvent

from core.session import SessionState
from ui.theme import COLORS


class OverlayBar(QWidget):
    """Semi-transparent bar that renders with blur-like dark background."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(10, 10, 11, 210))
        p.end()


def _tool_btn(label: str, tooltip: str, width: int = 80) -> QPushButton:
    btn = QPushButton(label)
    btn.setToolTip(tooltip)
    btn.setFixedHeight(36)
    btn.setMinimumWidth(width)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            border: 1px solid {COLORS['border_base']};
            border-radius: 6px;
            color: {COLORS['text_secondary']};
            font-size: 12px;
            padding: 0 10px;
        }}
        QPushButton:hover {{
            background: {COLORS['bg_hover']};
            color: {COLORS['text_primary']};
            border-color: {COLORS['border_light']};
        }}
        QPushButton:pressed {{
            background: {COLORS['bg_active']};
        }}
        QPushButton:checked {{
            background: {COLORS['accent']}22;
            border-color: {COLORS['accent_dim']};
            color: {COLORS['accent']};
        }}
    """)
    return btn


class TopBar(OverlayBar):
    """Top HUD — image counter, session progress."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(48)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(16)

        self._counter_lbl = QLabel("1 / 1")
        self._counter_lbl.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 14px;
            font-weight: 600;
            background: transparent;
        """)

        self._state_lbl = QLabel("")
        self._state_lbl.setStyleSheet(f"""
            color: {COLORS['accent']};
            font-size: 12px;
            font-weight: 500;
            background: transparent;
        """)

        lay.addWidget(self._counter_lbl)
        lay.addWidget(self._state_lbl)
        lay.addStretch()

    def update_counter(self, pos: int, total: int) -> None:
        self._counter_lbl.setText(f"{pos} / {total}")

    def set_state_label(self, text: str) -> None:
        self._state_lbl.setText(text)


class BottomBar(OverlayBar):
    """
    Bottom toolbar — progress bar, controls, transforms, end.
    """

    pause_clicked    = Signal()
    next_clicked     = Signal()
    prev_clicked     = Signal()
    end_clicked      = Signal()
    mirror_toggled   = Signal(bool)
    gray_toggled     = Signal(bool)
    fullscreen_toggled = Signal()
    timer_toggled    = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Progress bar (thin strip at very top of bottom bar)
        self._progress = QProgressBar()
        self._progress.setFixedHeight(3)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background: {COLORS['bg_elevated']};
                border: none;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {COLORS['accent_dim']}, stop:1 {COLORS['accent']});
            }}
        """)
        outer.addWidget(self._progress)

        # Main controls row
        ctrl = QWidget()
        ctrl.setStyleSheet("background: transparent;")
        ctrl.setFixedHeight(56)
        clay = QHBoxLayout(ctrl)
        clay.setContentsMargins(16, 0, 16, 0)
        clay.setSpacing(8)

        # Navigation
        self._prev_btn = _tool_btn("◀  Prev", "Previous (←/P)", 80)
        self._pause_btn = _tool_btn("⏸  Pause", "Pause/Resume (Space)", 96)
        self._next_btn = _tool_btn("Next  ▶", "Next (→/N)", 80)

        self._prev_btn.clicked.connect(self.prev_clicked)
        self._pause_btn.clicked.connect(self.pause_clicked)
        self._next_btn.clicked.connect(self.next_clicked)

        clay.addWidget(self._prev_btn)
        clay.addWidget(self._pause_btn)
        clay.addWidget(self._next_btn)

        clay.addSpacing(16)

        # Transform toggles
        self._mirror_btn = _tool_btn("⇆  Mirror", "Mirror (M)")
        self._mirror_btn.setCheckable(True)
        self._mirror_btn.toggled.connect(self.mirror_toggled)

        self._gray_btn = _tool_btn("◑  Gray", "Grayscale (G)")
        self._gray_btn.setCheckable(True)
        self._gray_btn.toggled.connect(self.gray_toggled)

        clay.addWidget(self._mirror_btn)
        clay.addWidget(self._gray_btn)

        clay.addStretch()

        # Right controls
        self._timer_btn = _tool_btn("⏱", "Toggle timer (T)", 40)
        self._fs_btn    = _tool_btn("⛶", "Fullscreen (F)",   40)
        self._end_btn   = _tool_btn("■  End", "End session (Esc)", 80)
        self._end_btn.setStyleSheet(self._end_btn.styleSheet() + f"""
            QPushButton {{ color: {COLORS['error']}; border-color: {COLORS['error']}44; }}
            QPushButton:hover {{ background: {COLORS['error']}18; }}
        """)

        self._timer_btn.clicked.connect(self.timer_toggled)
        self._fs_btn.clicked.connect(self.fullscreen_toggled)
        self._end_btn.clicked.connect(self.end_clicked)

        clay.addWidget(self._timer_btn)
        clay.addWidget(self._fs_btn)
        clay.addSpacing(8)
        clay.addWidget(self._end_btn)

        outer.addWidget(ctrl)

        # Filename strip
        self._fname_bar = QWidget()
        self._fname_bar.setFixedHeight(22)
        self._fname_bar.setStyleSheet("background: transparent;")
        flay = QHBoxLayout(self._fname_bar)
        flay.setContentsMargins(20, 0, 20, 0)
        self._fname_lbl = QLabel("")
        self._fname_lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
        flay.addWidget(self._fname_lbl)
        outer.addWidget(self._fname_bar)

    def set_progress(self, pos: int, total: int) -> None:
        if total > 0:
            self._progress.setMaximum(total)
            self._progress.setValue(pos)

    def set_paused(self, paused: bool) -> None:
        self._pause_btn.setText("▶  Resume" if paused else "⏸  Pause")

    def set_filename(self, name: str, visible: bool = True) -> None:
        self._fname_lbl.setText(name)
        self._fname_bar.setVisible(visible)

    def reset_toggles(self) -> None:
        self._mirror_btn.blockSignals(True)
        self._gray_btn.blockSignals(True)
        self._mirror_btn.setChecked(False)
        self._gray_btn.setChecked(False)
        self._mirror_btn.blockSignals(False)
        self._gray_btn.blockSignals(False)


class ToolbarOverlay(QWidget):
    """
    Composite overlay — wraps TopBar + BottomBar.
    Auto-hides after inactivity using opacity fade.
    Parent must be the session window (full size).
    """

    pause_clicked      = Signal()
    next_clicked       = Signal()
    prev_clicked       = Signal()
    end_clicked        = Signal()
    mirror_toggled     = Signal(bool)
    gray_toggled       = Signal(bool)
    fullscreen_toggled = Signal()
    timer_toggled      = Signal()

    HIDE_DELAY_MS = 3000   # hide after 3s of no movement

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(1.0)

        self._fade_anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_anim.setDuration(400)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(self.HIDE_DELAY_MS)
        self._hide_timer.timeout.connect(self._fade_out)

        self._visible_flag = True

        # Top and bottom bars
        self.top_bar    = TopBar(self)
        self.bottom_bar = BottomBar(self)

        # Wire signals
        self.bottom_bar.pause_clicked.connect(self.pause_clicked)
        self.bottom_bar.next_clicked.connect(self.next_clicked)
        self.bottom_bar.prev_clicked.connect(self.prev_clicked)
        self.bottom_bar.end_clicked.connect(self.end_clicked)
        self.bottom_bar.mirror_toggled.connect(self.mirror_toggled)
        self.bottom_bar.gray_toggled.connect(self.gray_toggled)
        self.bottom_bar.fullscreen_toggled.connect(self.fullscreen_toggled)
        self.bottom_bar.timer_toggled.connect(self.timer_toggled)

        self._schedule_hide()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._reposition()

    def _reposition(self) -> None:
        w, h = self.width(), self.height()
        self.top_bar.setGeometry(0, 0, w, self.top_bar.height())
        bh = self.bottom_bar.sizeHint().height()
        self.bottom_bar.setGeometry(0, h - bh, w, bh)

    def show_controls(self) -> None:
        """Call on mouse movement to reveal overlay."""
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._effect.opacity())
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()
        self._visible_flag = True
        self._schedule_hide()

    def _fade_out(self) -> None:
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._effect.opacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()
        self._visible_flag = False

    def _schedule_hide(self) -> None:
        self._hide_timer.stop()
        self._hide_timer.start()

    def keep_visible(self) -> None:
        """Call to prevent auto-hide (e.g., during pause)."""
        self._hide_timer.stop()
        self._fade_anim.stop()
        self._effect.setOpacity(1.0)
        self._visible_flag = True

    def resume_auto_hide(self) -> None:
        self._schedule_hide()
