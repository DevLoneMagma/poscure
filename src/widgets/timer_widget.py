"""
Poscure Timer Widget — animated countdown ring with number display.
Used as a floating overlay during sessions.
"""

from __future__ import annotations
import math

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QRect, QRectF, QPointF, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QBrush,
    QRadialGradient, QPaintEvent, QFontMetrics
)

from ui.theme import COLORS


class TimerWidget(QWidget):
    """
    Compact arc ring + countdown number.
    The arc depletes clockwise from 12 o'clock as time runs out.
    Flashes red when <= 5 seconds remain.
    """

    SIZE_MAP = {
        "small":  80,
        "medium": 110,
        "large":  140,
    }

    def __init__(self, parent=None, size_name: str = "large") -> None:
        super().__init__(parent)
        self._total    = 30
        self._remain   = 30
        self._progress = 1.0    # animated display value
        self._target   = 1.0
        self._flash    = False
        self._flash_state = False

        sz = self.SIZE_MAP.get(size_name, 140)
        self.setFixedSize(sz, sz)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Smooth ring animation (~60fps)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._step)
        self._anim_timer.start()

        # Flash timer for warning state
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(500)
        self._flash_timer.timeout.connect(self._toggle_flash)

    def set_time(self, total: int, remaining: int) -> None:
        self._total   = max(1, total)
        self._remain  = remaining
        self._target  = max(0.0, remaining / self._total)

        warn = remaining <= 5 and remaining > 0
        if warn and not self._flash:
            self._flash = True
            self._flash_timer.start()
        elif not warn and self._flash:
            self._flash = False
            self._flash_state = False
            self._flash_timer.stop()

        self.update()

    def reset(self) -> None:
        self._progress = 1.0
        self._target   = 1.0
        self._remain   = self._total
        self._flash    = False
        self._flash_state = False
        self._flash_timer.stop()
        self.update()

    def _step(self) -> None:
        diff = self._target - self._progress
        if abs(diff) > 0.001:
            self._progress += diff * 0.15
            self.update()
        elif self._progress != self._target:
            self._progress = self._target
            self.update()

    def _toggle_flash(self) -> None:
        self._flash_state = not self._flash_state
        self.update()

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        sz     = min(self.width(), self.height())
        margin = sz * 0.08
        ring_w = max(3, sz * 0.06)
        cx, cy = self.width() / 2, self.height() / 2
        rect   = QRectF(margin, margin, sz - 2 * margin, sz - 2 * margin)

        # ── Background circle (dark translucent) ──
        p.setBrush(QBrush(QColor(10, 10, 11, 180)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(rect)

        # ── Track ring ──
        pen = QPen(QColor(COLORS["ring_track"]), ring_w, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(rect.adjusted(ring_w / 2, ring_w / 2,
                                    -ring_w / 2, -ring_w / 2))

        # ── Fill arc ──
        if self._progress > 0.001:
            span  = int(self._progress * 360 * 16)
            start = 90 * 16  # 12 o'clock

            # Color: gold → orange-red as time runs out
            if self._flash and self._flash_state:
                fill_color = QColor("#C05050")
            elif self._progress < 0.25:
                fill_color = QColor("#C87050")
            else:
                fill_color = QColor(COLORS["ring_fill"])

            pen2 = QPen(fill_color, ring_w, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap)
            p.setPen(pen2)
            arc_rect = rect.adjusted(ring_w / 2, ring_w / 2,
                                     -ring_w / 2, -ring_w / 2)
            p.drawArc(arc_rect, start, -span)

        # ── Countdown number ──
        font_size = max(14, int(sz * 0.28))
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        p.setFont(font)

        if self._flash and self._flash_state:
            text_color = QColor("#E05050")
        else:
            text_color = QColor(COLORS["text_primary"])

        p.setPen(text_color)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(max(0, self._remain)))

        p.end()
