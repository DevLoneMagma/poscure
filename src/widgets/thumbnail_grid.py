"""
Poscure ThumbnailGrid — virtualized, lazy-loading image grid.
"""

from __future__ import annotations
import threading
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QScrollArea, QGridLayout, QVBoxLayout,
    QHBoxLayout, QLabel, QFrame, QSizePolicy, QAbstractScrollArea,
    QApplication
)
from PySide6.QtCore import (
    Qt, Signal, QThread, QObject, QRunnable, QThreadPool,
    QTimer, QSize, QPoint
)
from PySide6.QtGui import (
    QPixmap, QColor, QPainter, QBrush, QPen, QPaintEvent,
    QMouseEvent, QCursor
)

from core.library import ImageEntry
from core.cache import get_cache
from utils.image_utils import thumbnail_from_bytes
from ui.theme import COLORS


# ── Thumbnail loader ───────────────────────────────────────────────────────────

class ThumbLoader(QObject):
    loaded = Signal(str, bytes)  # path, png_bytes

    def __init__(self, path: str, quality: str) -> None:
        super().__init__()
        self.path    = path
        self.quality = quality

    def run(self) -> None:
        data = get_cache().generate_thumbnail(self.path, self.quality)
        if data:
            self.loaded.emit(self.path, data)


class ThumbRunnable(QRunnable):
    def __init__(self, loader: ThumbLoader) -> None:
        super().__init__()
        self.loader = loader
        self.setAutoDelete(False)

    def run(self) -> None:
        self.loader.run()


# ── Single thumbnail cell ──────────────────────────────────────────────────────

class ThumbnailCell(QFrame):
    """
    Individual thumbnail tile. Shows image, selection overlay,
    and hover info tooltip.
    """
    clicked       = Signal(object, bool)   # (ImageEntry, ctrl_held)
    double_clicked = Signal(object)         # ImageEntry

    PLACEHOLDER_COLOR = QColor(COLORS["bg_elevated"])
    SELECT_COLOR      = QColor(COLORS["accent"] + "55")
    SELECT_BORDER     = QColor(COLORS["accent"])

    def __init__(self, entry: ImageEntry, cell_size: int = 160,
                 parent=None) -> None:
        super().__init__(parent)
        self.entry       = entry
        self.cell_size   = cell_size
        self._pixmap:    Optional[QPixmap] = None
        self._selected   = False
        self._hovered    = False

        self.setFixedSize(cell_size, cell_size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def set_pixmap(self, pm: QPixmap) -> None:
        self._pixmap = pm
        self.update()

    def set_selected(self, v: bool) -> None:
        self._selected = v
        self.update()

    def is_selected(self) -> bool:
        return self._selected

    def toggle_selected(self) -> None:
        self.set_selected(not self._selected)

    # ── painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()

        # Background
        p.fillRect(r, self.PLACEHOLDER_COLOR)

        if self._pixmap:
            # Scale to fill cell
            scaled = self._pixmap.scaled(
                self.cell_size, self.cell_size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.cell_size - scaled.width())  // 2
            y = (self.cell_size - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
        else:
            # Loading placeholder shimmer
            p.setPen(QPen(QColor(COLORS["border_dim"])))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, "···")

        # Selection overlay
        if self._selected:
            p.fillRect(r, self.SELECT_COLOR)
            pen = QPen(self.SELECT_BORDER, 2)
            p.setPen(pen)
            p.drawRect(r.adjusted(1, 1, -1, -1))

        # Hover overlay (subtle)
        if self._hovered and not self._selected:
            p.fillRect(r, QColor(255, 255, 255, 12))

        p.end()

    def enterEvent(self, e) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            ctrl = e.modifiers() & Qt.KeyboardModifier.ControlModifier
            self.clicked.emit(self.entry, bool(ctrl))
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.entry)
        super().mouseDoubleClickEvent(e)

    def toolTip(self) -> str:
        from utils.image_utils import human_size
        e = self.entry
        dims = f"{e.width}×{e.height}" if e.width else "?"
        return f"{e.filename}\n{dims}  ·  {human_size(e.file_size)}"

    def event(self, e) -> bool:
        if e.type() == e.Type.ToolTip:
            from PySide6.QtWidgets import QToolTip
            QToolTip.showText(QCursor.pos(), self.toolTip(), self)
            return True
        return super().event(e)


# ── Grid container ────────────────────────────────────────────────────────────

class ThumbnailGrid(QWidget):
    """
    Responsive thumbnail grid with lazy loading, multi-select,
    and column-count control.
    """
    selection_changed = Signal(list)         # list of selected ImageEntry
    image_activated   = Signal(object)        # ImageEntry (double-click)

    def __init__(self, parent=None,
                 columns: int = 5,
                 quality: str = "medium") -> None:
        super().__init__(parent)
        self._columns  = columns
        self._quality  = quality
        self._entries: list[ImageEntry]      = []
        self._cells:   dict[str, ThumbnailCell] = {}  # path → cell
        self._selected: set[str]             = set()
        self._pool     = QThreadPool.globalInstance()
        self._pool.setMaxThreadCount(4)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._grid      = QGridLayout(self._container)
        self._grid.setSpacing(4)
        self._grid.setContentsMargins(4, 4, 4, 4)
        self._scroll.setWidget(self._container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

        # Deferred load timer (avoids thrashing during rapid updates)
        self._pending_paths: list[str] = []
        self._load_timer = QTimer(self)
        self._load_timer.setInterval(50)
        self._load_timer.timeout.connect(self._process_pending)

    # ── public API ────────────────────────────────────────────────────────────

    def set_entries(self, entries: list[ImageEntry]) -> None:
        self._entries = entries
        self._rebuild()

    def set_columns(self, n: int) -> None:
        self._columns = max(3, min(8, n))
        self._rebuild()

    def set_quality(self, q: str) -> None:
        self._quality = q
        # Clear pixmap cache and reload
        for cell in self._cells.values():
            cell.set_pixmap(None)
        self._schedule_loads(list(self._cells.keys()))

    def select_all(self) -> None:
        self._selected = {e.path for e in self._entries}
        for cell in self._cells.values():
            cell.set_selected(True)
        self._emit_selection()

    def clear_selection(self) -> None:
        self._selected.clear()
        for cell in self._cells.values():
            cell.set_selected(False)
        self._emit_selection()

    def selected_entries(self) -> list[ImageEntry]:
        return [e for e in self._entries if e.path in self._selected]

    def selected_count(self) -> int:
        return len(self._selected)

    # ── internal ──────────────────────────────────────────────────────────────

    def _cell_size(self) -> int:
        # Derive cell size from columns and available width
        w = self.width() or 800
        spacing = 4 * (self._columns + 1)
        return max(80, (w - spacing) // self._columns)

    def _rebuild(self) -> None:
        # Clear grid
        for cell in self._cells.values():
            cell.setParent(None)
        self._cells.clear()

        cell_size = self._cell_size()
        paths_to_load = []

        for idx, entry in enumerate(self._entries):
            row, col = divmod(idx, self._columns)
            cell = ThumbnailCell(entry, cell_size, self._container)
            cell.clicked.connect(self._on_cell_click)
            cell.double_clicked.connect(self.image_activated)
            cell.set_selected(entry.path in self._selected)
            self._grid.addWidget(cell, row, col)
            self._cells[entry.path] = cell
            paths_to_load.append(entry.path)

        self._schedule_loads(paths_to_load)

    def _schedule_loads(self, paths: list[str]) -> None:
        self._pending_paths = paths[:]
        self._load_timer.start()

    def _process_pending(self) -> None:
        # Load 20 thumbnails per tick to keep UI responsive
        batch = self._pending_paths[:20]
        self._pending_paths = self._pending_paths[20:]
        if not self._pending_paths:
            self._load_timer.stop()

        for path in batch:
            if path not in self._cells:
                continue
            # Check cache first (synchronous, fast)
            data = get_cache().get_thumbnail(path, self._quality)
            if data:
                pm = thumbnail_from_bytes(data)
                if pm and path in self._cells:
                    self._cells[path].set_pixmap(pm)
            else:
                # Background generation
                loader = ThumbLoader(path, self._quality)
                loader.loaded.connect(self._on_thumb_loaded)
                runnable = ThumbRunnable(loader)
                self._pool.start(runnable)

    def _on_thumb_loaded(self, path: str, data: bytes) -> None:
        if path not in self._cells:
            return
        pm = thumbnail_from_bytes(data)
        if pm:
            self._cells[path].set_pixmap(pm)

    def _on_cell_click(self, entry: ImageEntry, ctrl: bool) -> None:
        if ctrl:
            # Multi-select
            if entry.path in self._selected:
                self._selected.discard(entry.path)
                self._cells[entry.path].set_selected(False)
            else:
                self._selected.add(entry.path)
                self._cells[entry.path].set_selected(True)
        else:
            # Single select
            prev = set(self._selected)
            self._selected.clear()
            self._selected.add(entry.path)
            for p, cell in self._cells.items():
                cell.set_selected(p == entry.path)
        self._emit_selection()

    def _emit_selection(self) -> None:
        self.selection_changed.emit(self.selected_entries())

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        # Rebuild on resize for responsive columns
        QTimer.singleShot(100, self._rebuild)
