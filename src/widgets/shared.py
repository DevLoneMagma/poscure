"""
Poscure shared widgets — reusable polished primitives.
"""

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout,
    QPushButton, QGraphicsOpacityEffect, QSizePolicy
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QSize,
    Property, QPoint, QTimer
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPaintEvent
)

from ui.theme import COLORS


# ── Animated fade widget ───────────────────────────────────────────────────────

class FadeWidget(QWidget):
    """Widget that can fade in/out smoothly."""

    def __init__(self, parent=None, duration: int = 200) -> None:
        super().__init__(parent)
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def fade_in(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._effect.opacity())
        self._anim.setEndValue(1.0)
        self.show()
        self._anim.start()

    def fade_out(self, hide_after: bool = True) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._effect.opacity())
        self._anim.setEndValue(0.0)
        if hide_after:
            self._anim.finished.connect(self._on_fade_out_done)
        self._anim.start()

    def _on_fade_out_done(self) -> None:
        self.hide()
        try:
            self._anim.finished.disconnect(self._on_fade_out_done)
        except Exception:
            pass


# ── Card panel ────────────────────────────────────────────────────────────────

class Card(QFrame):
    """Rounded dark card with optional title."""

    def __init__(self, title: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(f"""
            #card {{
                background: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border_base']};
                border-radius: 10px;
            }}
        """)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(12)

        if title:
            lbl = QLabel(title.upper())
            lbl.setProperty("class", "subheading")
            lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px; letter-spacing: 1px; font-weight: 600;")
            self._layout.addWidget(lbl)

    def content_layout(self) -> QVBoxLayout:
        return self._layout


# ── Horizontal divider ────────────────────────────────────────────────────────

class HDivider(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet(f"background: {COLORS['border_base']}; max-height: 1px;")
        self.setFixedHeight(1)


# ── Icon button (square, no text) ─────────────────────────────────────────────

class IconButton(QPushButton):
    def __init__(self, icon_text: str = "●", tooltip: str = "",
                 size: int = 32, parent=None) -> None:
        super().__init__(icon_text, parent)
        self.setFixedSize(size, size)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLORS['text_secondary']};
                font-size: 14px;
                border-radius: {size//2}px;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_hover']};
                color: {COLORS['text_primary']};
            }}
            QPushButton:pressed {{
                background: {COLORS['bg_active']};
            }}
        """)


# ── Pill badge ────────────────────────────────────────────────────────────────

class PillBadge(QLabel):
    def __init__(self, text: str = "", color: str = None, parent=None) -> None:
        super().__init__(text, parent)
        bg = color or COLORS['bg_elevated']
        self.setStyleSheet(f"""
            background: {bg};
            color: {COLORS['text_secondary']};
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: 500;
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


# ── Section label ─────────────────────────────────────────────────────────────

class SectionLabel(QLabel):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text.upper(), parent)
        self.setStyleSheet(f"""
            color: {COLORS['text_tertiary']};
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1.2px;
            padding: 4px 0;
        """)


# ── Circular progress ring ────────────────────────────────────────────────────

class RingWidget(QWidget):
    """
    Thin arc ring showing progress 0–1.
    Used for the session timer.
    """

    def __init__(self, parent=None, size: int = 80,
                 track_color: str = None, fill_color: str = None) -> None:
        super().__init__(parent)
        self._size     = size
        self._progress = 1.0   # 1.0 = full, 0.0 = empty
        self._track    = QColor(track_color or COLORS["ring_track"])
        self._fill     = QColor(fill_color  or COLORS["ring_fill"])
        self.setFixedSize(size, size)

        # Smooth animation
        self._anim_value = 1.0
        self._target     = 1.0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60fps
        self._anim_timer.timeout.connect(self._step_anim)

    def set_progress(self, value: float, animate: bool = True) -> None:
        self._target = max(0.0, min(1.0, value))
        if animate and abs(self._target - self._anim_value) > 0.001:
            self._anim_timer.start()
        else:
            self._anim_value = self._target
            self._anim_timer.stop()
            self.update()

    def _step_anim(self) -> None:
        diff = self._target - self._anim_value
        self._anim_value += diff * 0.18
        if abs(diff) < 0.001:
            self._anim_value = self._target
            self._anim_timer.stop()
        self.update()

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin  = 5
        rect    = self.rect().adjusted(margin, margin, -margin, -margin)
        span    = int(self._anim_value * 360 * 16)  # Qt uses 1/16 degree
        start   = 90 * 16   # 12 o'clock

        # Track
        pen = QPen(self._track, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        p.drawArc(rect, 0, 360 * 16)

        # Fill arc
        if span > 0:
            pen.setColor(self._fill)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawArc(rect, start, -span)

        p.end()


# ── Animated toggle button ────────────────────────────────────────────────────

class ToggleButton(QPushButton):
    """Checkable button that animates its background."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        self.toggled.connect(self._update_style)

    def _update_style(self) -> None:
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['accent']};
                    color: #0A0A0B;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: 600;
                    font-size: 13px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['bg_elevated']};
                    color: {COLORS['text_secondary']};
                    border: 1px solid {COLORS['border_base']};
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: {COLORS['bg_hover']};
                    color: {COLORS['text_primary']};
                }}
            """)


# ── Stat tile ─────────────────────────────────────────────────────────────────

class StatTile(QFrame):
    """Small number + label stat display tile."""

    def __init__(self, value: str = "0", label: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statTile")
        self.setStyleSheet(f"""
            #statTile {{
                background: {COLORS['bg_elevated']};
                border: 1px solid {COLORS['border_dim']};
                border-radius: 8px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(2)

        self._val_lbl = QLabel(value)
        self._val_lbl.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};")
        self._val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._key_lbl = QLabel(label.upper())
        self._key_lbl.setStyleSheet(f"font-size: 10px; color: {COLORS['text_tertiary']}; letter-spacing: 1px;")
        self._key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lay.addWidget(self._val_lbl)
        lay.addWidget(self._key_lbl)

    def set_value(self, v: str) -> None:
        self._val_lbl.setText(v)

    def set_label(self, l: str) -> None:
        self._key_lbl.setText(l.upper())


# ── Toast notification ────────────────────────────────────────────────────────

class Toast(FadeWidget):
    """Temporary floating notification that auto-dismisses."""

    def __init__(self, parent: QWidget, message: str,
                 duration_ms: int = 2500, color: str = None) -> None:
        super().__init__(parent, duration=250)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        bg = color or COLORS["bg_elevated"]

        self.setStyleSheet(f"""
            background: {bg};
            border: 1px solid {COLORS['border_light']};
            border-radius: 8px;
            padding: 10px 18px;
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(message)
        lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px;")
        lay.addWidget(lbl)
        self.adjustSize()

        # Center bottom of parent
        pw, ph = parent.width(), parent.height()
        tw, th = self.width(), self.height()
        self.move((pw - tw) // 2, ph - th - 40)

        self.fade_in()
        QTimer.singleShot(duration_ms, self.fade_out)
