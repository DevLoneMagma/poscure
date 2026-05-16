"""
Poscure Session Window — fullscreen drawing session.
Handles image display, preloading, transforms, overlays, hotkeys.

CRASH FIX: Preload threads now properly tracked and cleaned up.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QSizePolicy,
    QApplication, QGraphicsOpacityEffect, QPushButton, QHBoxLayout
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QThread, QObject,
    QPropertyAnimation, QEasingCurve
)
from PySide6.QtGui import (
    QPixmap, QColor, QPainter, QPaintEvent,
    QMouseEvent, QKeyEvent, QResizeEvent
)

from core.session import Session, SessionConfig, SessionState, SessionStats
from core.library import ImageEntry
from utils.image_utils import load_pixmap, apply_grayscale, apply_mirror, fit_pixmap
from widgets.timer_widget import TimerWidget
from widgets.toolbar_overlay import ToolbarOverlay
from utils.hotkeys import HotkeyManager
from core.settings import get_settings
from ui.theme import COLORS


# ── Background preloader ──────────────────────────────────────────────────────

class PreloadWorker(QObject):
    loaded = Signal(str, object)   # path, QPixmap or None

    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path

    def run(self) -> None:
        pm = load_pixmap(self.path)
        self.loaded.emit(self.path, pm)


# ── Image canvas with cross-fade ──────────────────────────────────────────────

class ImageCanvas(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {COLORS['bg_deep']};")
        self._current:  Optional[QPixmap] = None
        self._previous: Optional[QPixmap] = None
        self._opacity   = 1.0
        self._fit_mode  = "fit"

        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(16)
        self._fade_timer.timeout.connect(self._fade_step)

    def set_fit_mode(self, mode: str) -> None:
        self._fit_mode = mode
        self.update()

    def set_pixmap(self, pm: Optional[QPixmap], animate: bool = True) -> None:
        if animate and self._current:
            self._previous = self._current
            self._opacity  = 0.0
        else:
            self._previous = None
            self._opacity  = 1.0
        self._current = pm
        if animate:
            self._fade_timer.start()
        self.update()

    def _fade_step(self) -> None:
        self._opacity = min(1.0, self._opacity + 0.08)
        self.update()
        if self._opacity >= 1.0:
            self._fade_timer.stop()
            self._previous = None

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor(COLORS["bg_deep"]))

        def _draw(pm: QPixmap, alpha: float) -> None:
            if pm is None:
                return
            scaled = fit_pixmap(pm, w, h, self._fit_mode)
            x = (w - scaled.width())  // 2
            y = (h - scaled.height()) // 2
            p.setOpacity(alpha)
            p.drawPixmap(x, y, scaled)

        if self._previous and self._opacity < 1.0:
            _draw(self._previous, 1.0 - self._opacity)
        if self._current:
            _draw(self._current, self._opacity)
        p.end()


# ── Break overlay ─────────────────────────────────────────────────────────────

class BreakOverlay(QWidget):
    skip_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(16)

        self._title = QLabel("Break Time")
        self._title.setStyleSheet(f"color:{COLORS['text_primary']};font-size:32px;font-weight:700;")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._sub = QLabel("Relax your hand. Next set starts soon.")
        self._sub.setStyleSheet(f"color:{COLORS['text_secondary']};font-size:14px;")
        self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._time_lbl = QLabel("0:30")
        self._time_lbl.setStyleSheet(f"color:{COLORS['accent']};font-size:48px;font-weight:700;")
        self._time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        skip = QPushButton("Skip Break")
        skip.setFixedSize(130, 36)
        skip.setStyleSheet(f"""
            QPushButton {{background:transparent;border:1px solid {COLORS['border_light']};
            color:{COLORS['text_secondary']};border-radius:6px;font-size:13px;}}
            QPushButton:hover {{background:{COLORS['bg_hover']};color:{COLORS['text_primary']};}}
        """)
        skip.clicked.connect(self.skip_clicked)

        lay.addStretch()
        lay.addWidget(self._title)
        lay.addWidget(self._sub)
        lay.addSpacing(12)
        lay.addWidget(self._time_lbl)
        lay.addSpacing(20)
        lay.addWidget(skip, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addStretch()

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(10, 10, 11, 220))
        p.end()

    def set_remaining(self, secs: int) -> None:
        m, s = divmod(secs, 60)
        self._time_lbl.setText(f"{m}:{s:02d}")


# ── Session summary overlay ───────────────────────────────────────────────────

class SummaryOverlay(QWidget):
    restart_clicked = Signal()
    library_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(12)

        title = QLabel("Session Complete")
        title.setStyleSheet(f"color:{COLORS['text_primary']};font-size:28px;font-weight:700;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet(f"color:{COLORS['text_secondary']};font-size:15px;")
        self._stats_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_row = QWidget()
        btn_row.setStyleSheet("background:transparent;")
        blay = QHBoxLayout(btn_row)
        blay.setSpacing(12)
        blay.setContentsMargins(0, 0, 0, 0)

        restart = QPushButton("↺  Practice Again")
        restart.setFixedSize(160, 40)
        restart.setStyleSheet(f"""
            QPushButton {{background:{COLORS['accent']};color:#0A0A0B;border:none;
            border-radius:7px;font-size:13px;font-weight:700;}}
            QPushButton:hover {{background:#D9BA8F;}}
        """)
        restart.clicked.connect(self.restart_clicked)

        lib = QPushButton("← Back to Library")
        lib.setFixedSize(160, 40)
        lib.setStyleSheet(f"""
            QPushButton {{background:transparent;border:1px solid {COLORS['border_light']};
            color:{COLORS['text_secondary']};border-radius:7px;font-size:13px;}}
            QPushButton:hover {{background:{COLORS['bg_hover']};color:{COLORS['text_primary']};}}
        """)
        lib.clicked.connect(self.library_clicked)

        blay.addWidget(restart)
        blay.addWidget(lib)

        lay.addStretch()
        lay.addWidget(title)
        lay.addSpacing(8)
        lay.addWidget(self._stats_lbl)
        lay.addSpacing(24)
        lay.addWidget(btn_row, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addStretch()

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(10, 10, 11, 235))
        p.end()

    def set_stats(self, stats: SessionStats) -> None:
        elapsed = int(stats.elapsed)
        m, s = divmod(elapsed, 60)
        self._stats_lbl.setText(f"{stats.images_shown} images  ·  {m}m {s:02d}s")


# ── Main Session Window ───────────────────────────────────────────────────────

class SessionWindow(QWidget):
    session_ended = Signal()

    def __init__(self, config: SessionConfig, parent=None) -> None:
        super().__init__(parent)
        self._config    = config
        self._settings  = get_settings()
        self._session   = Session(config)
        self._grayscale = False
        self._mirror    = False
        self._fit_mode  = self._settings.get("default_fit_mode", "fit")
        self._show_timer = self._settings.get("show_timer", True)
        self._show_fname = self._settings.get("show_filename", False)

        self._preload_cache: dict[str, QPixmap] = {}
        # (thread, worker) pairs — kept alive until thread finishes
        self._preload_workers: list[tuple[QThread, PreloadWorker]] = []
        self._preload_count = self._settings.get("preload_count", 3)

        self.setStyleSheet(f"background:{COLORS['bg_deep']};")
        self.setMouseTracking(True)
        self._build()
        self._connect_session()
        self._setup_hotkeys()

        self.showFullScreen()
        QTimer.singleShot(100, self._session.start)

    def _build(self) -> None:
        self._canvas = ImageCanvas(self)
        self._canvas.set_fit_mode(self._fit_mode)
        self._canvas.setGeometry(self.rect())

        sz_name = self._settings.get("timer_size", "large")
        self._timer_widget = TimerWidget(self, size_name=sz_name)
        self._timer_widget.setVisible(self._show_timer)

        self._toolbar = ToolbarOverlay(self)
        self._toolbar.setGeometry(self.rect())

        self._break_overlay = BreakOverlay(self)
        self._break_overlay.setGeometry(self.rect())
        self._break_overlay.skip_clicked.connect(self._on_break_skipped)

        self._summary = SummaryOverlay(self)
        self._summary.setGeometry(self.rect())
        self._summary.restart_clicked.connect(self._on_restart)
        self._summary.library_clicked.connect(self._on_library)

    def _connect_session(self) -> None:
        s = self._session
        s.image_changed.connect(self._on_image_changed)
        s.timer_tick.connect(self._on_timer_tick)
        s.state_changed.connect(self._on_state_changed)
        s.break_started.connect(self._on_break_started)
        s.break_tick.connect(self._on_break_tick)
        s.session_finished.connect(self._on_session_finished)

    def _setup_hotkeys(self) -> None:
        self._hk = HotkeyManager(self, self._settings)
        self._hk.register("pause_resume",  self._session.toggle_pause)
        self._hk.register("next",          self._session.next_image)
        self._hk.register("previous",      self._session.previous_image)
        self._hk.register("fullscreen",    self._toggle_fullscreen)
        self._hk.register("grayscale",     self._toggle_grayscale)
        self._hk.register("mirror",        self._toggle_mirror)
        self._hk.register("toggle_timer",  self._toggle_timer)
        self._hk.register("end_session",   self._confirm_end)

        self._toolbar.pause_clicked.connect(self._session.toggle_pause)
        self._toolbar.next_clicked.connect(self._session.next_image)
        self._toolbar.prev_clicked.connect(self._session.previous_image)
        self._toolbar.end_clicked.connect(self._confirm_end)
        self._toolbar.mirror_toggled.connect(self._set_mirror)
        self._toolbar.gray_toggled.connect(self._set_grayscale)
        self._toolbar.fullscreen_toggled.connect(self._toggle_fullscreen)
        self._toolbar.timer_toggled.connect(self._toggle_timer)

    # ── Session handlers ──────────────────────────────────────────────────────

    def _on_image_changed(self, entry: ImageEntry, pos: int, total: int) -> None:
        pm = self._get_pixmap(entry.path)
        if pm:
            if self._grayscale:
                pm = apply_grayscale(pm)
            if self._mirror:
                pm = apply_mirror(pm)
        self._canvas.set_pixmap(pm, animate=True)
        self._toolbar.top_bar.update_counter(pos, total)
        self._toolbar.bottom_bar.set_progress(pos, total)
        self._toolbar.bottom_bar.set_filename(entry.filename, self._show_fname)
        self._preload_ahead()

    def _on_timer_tick(self, remaining: int) -> None:
        self._timer_widget.set_time(self._config.duration, remaining)

    def _on_state_changed(self, state: SessionState) -> None:
        paused = state == SessionState.PAUSED
        self._toolbar.bottom_bar.set_paused(paused)
        if paused:
            self._toolbar.top_bar.set_state_label("PAUSED")
            self._toolbar.keep_visible()
        elif state == SessionState.RUNNING:
            self._toolbar.top_bar.set_state_label("")
            self._toolbar.resume_auto_hide()

    def _on_break_started(self, duration: int) -> None:
        self._break_overlay.set_remaining(duration)
        self._break_overlay.show()
        self._break_overlay.raise_()

    def _on_break_tick(self, remaining: int) -> None:
        self._break_overlay.set_remaining(remaining)

    def _on_break_skipped(self) -> None:
        self._break_overlay.hide()
        self._session._break_timer.stop()
        self._session._set_state(SessionState.RUNNING)
        self._session._advance(from_history=False)

    def _on_session_finished(self, stats: SessionStats) -> None:
        self._break_overlay.hide()
        self._summary.set_stats(stats)
        self._summary.show()
        self._summary.raise_()

    # ── Controls ──────────────────────────────────────────────────────────────

    def _toggle_grayscale(self) -> None:
        self._set_grayscale(not self._grayscale)

    def _set_grayscale(self, v: bool) -> None:
        self._grayscale = v
        self._refresh_display()

    def _toggle_mirror(self) -> None:
        self._set_mirror(not self._mirror)

    def _set_mirror(self, v: bool) -> None:
        self._mirror = v
        self._refresh_display()

    def _toggle_timer(self) -> None:
        self._show_timer = not self._show_timer
        self._timer_widget.setVisible(self._show_timer)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _confirm_end(self) -> None:
        self._session.end()

    def _refresh_display(self) -> None:
        entry = self._session.current_entry()
        if entry is None:
            return
        pm = self._get_pixmap(entry.path)
        if pm:
            if self._grayscale:
                pm = apply_grayscale(pm)
            if self._mirror:
                pm = apply_mirror(pm)
        self._canvas.set_pixmap(pm, animate=False)

    def _on_restart(self) -> None:
        self._summary.hide()
        self._session = Session(self._config)
        self._connect_session()
        self._canvas.set_pixmap(None, animate=False)
        self._timer_widget.reset()
        self._toolbar.bottom_bar.reset_toggles()
        self._grayscale = False
        self._mirror    = False
        QTimer.singleShot(100, self._session.start)

    def _on_library(self) -> None:
        self._summary.hide()
        self._cleanup_preload_threads()
        if self.isFullScreen():
            self.showNormal()
        self.session_ended.emit()

    # ── Preloading (CRASH-FIXED) ───────────────────────────────────────────────

    def _get_pixmap(self, path: str) -> Optional[QPixmap]:
        if path in self._preload_cache:
            return self._preload_cache[path]
        pm = load_pixmap(path)
        if pm:
            self._preload_cache[path] = pm
        return pm

    def _preload_ahead(self) -> None:
        queue = self._session._queue
        if not queue:
            return
        idx = self._session._current_idx
        for i in range(1, self._preload_count + 1):
            next_idx = (idx + i) % len(queue)
            path = queue[next_idx].path
            if path not in self._preload_cache:
                self._launch_preload(path)

        # Evict oldest entries to cap memory
        max_cached = self._preload_count + 8
        if len(self._preload_cache) > max_cached:
            keys = list(self._preload_cache.keys())
            for k in keys[:len(self._preload_cache) - max_cached]:
                del self._preload_cache[k]

    def _launch_preload(self, path: str) -> None:
        worker = PreloadWorker(path)
        thread = QThread(self)          # parent=self keeps alive
        worker.moveToThread(thread)

        Q = Qt.ConnectionType.QueuedConnection
        worker.loaded.connect(self._on_preloaded, Q)
        thread.started.connect(worker.run)

        # Clean up when done
        worker.loaded.connect(thread.quit, Q)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda t=thread, w=worker: self._cleanup_preload_pair(t, w))

        self._preload_workers.append((thread, worker))
        thread.start()

    def _on_preloaded(self, path: str, pm: QPixmap) -> None:
        if pm and not pm.isNull():
            self._preload_cache[path] = pm

    def _cleanup_preload_pair(self, thread: QThread, worker: PreloadWorker) -> None:
        try:
            self._preload_workers.remove((thread, worker))
        except ValueError:
            pass

    def _cleanup_preload_threads(self) -> None:
        for thread, worker in list(self._preload_workers):
            thread.quit()
            thread.wait(1000)
        self._preload_workers.clear()

    # ── Layout ────────────────────────────────────────────────────────────────

    def resizeEvent(self, e: QResizeEvent) -> None:
        super().resizeEvent(e)
        w, h = self.width(), self.height()
        self._canvas.setGeometry(0, 0, w, h)
        self._toolbar.setGeometry(0, 0, w, h)
        self._break_overlay.setGeometry(0, 0, w, h)
        self._summary.setGeometry(0, 0, w, h)
        self._position_timer()

    def _position_timer(self) -> None:
        pos_str = self._settings.get("timer_position", "top-right")
        tw, th = self._timer_widget.width(), self._timer_widget.height()
        w, h   = self.width(), self.height()
        margin, top_off = 20, 56
        positions = {
            "top-right":  (w - tw - margin, top_off),
            "top-left":   (margin, top_off),
            "top-center": ((w - tw) // 2, top_off),
        }
        x, y = positions.get(pos_str, positions["top-right"])
        self._timer_widget.move(x, y)
        self._timer_widget.raise_()

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        self._toolbar.show_controls()
        super().mouseMoveEvent(e)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        self._toolbar.show_controls()
        super().keyPressEvent(e)

    def closeEvent(self, e) -> None:
        self._cleanup_preload_threads()
        self._session.end()
        super().closeEvent(e)
