"""
Poscure Library View — left panel (folders) + right panel (grid browser).
"""

from __future__ import annotations
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QSplitter, QScrollArea, QFrame, QLineEdit, QComboBox,
    QFileDialog, QSizePolicy, QSpacerItem, QApplication,
    QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QTimer, QMimeData, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QColor

from core.library import Library, FolderEntry, ImageEntry, get_library
from core.settings import get_settings
from widgets.thumbnail_grid import ThumbnailGrid
from widgets.shared import (
    Card, HDivider, IconButton, SectionLabel, PillBadge,
    StatTile, Toast
)
from ui.theme import COLORS


# ── Folder row widget ─────────────────────────────────────────────────────────

class FolderRow(QFrame):
    remove_clicked  = Signal(str)
    refresh_clicked = Signal(str)
    recursive_toggled = Signal(str, bool)

    def __init__(self, entry: FolderEntry, parent=None) -> None:
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("folderRow")
        self._scanning = False
        self._build()
        self._update_style(False)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(8)

        # Folder icon + path
        icon = QLabel("📁")
        icon.setStyleSheet("font-size: 14px; background: transparent;")
        name = Path(self.entry.path).name
        self._name_lbl = QLabel(name)
        self._name_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px; font-weight: 500;")
        self._name_lbl.setToolTip(self.entry.path)

        top.addWidget(icon)
        top.addWidget(self._name_lbl, 1)

        self._refresh_btn = IconButton("↻", "Refresh folder", 24)
        self._remove_btn  = IconButton("✕", "Remove folder",  24)
        self._refresh_btn.setStyleSheet(self._refresh_btn.styleSheet() + f"color: {COLORS['accent_dim']};")
        self._remove_btn.setStyleSheet(self._remove_btn.styleSheet()   + f"color: {COLORS['error']};")
        self._refresh_btn.clicked.connect(lambda: self.refresh_clicked.emit(self.entry.path))
        self._remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.entry.path))
        top.addWidget(self._refresh_btn)
        top.addWidget(self._remove_btn)

        lay.addLayout(top)

        # Bottom: stats + recursive toggle
        bot = QHBoxLayout()
        bot.setSpacing(8)
        self._count_lbl = QLabel(f"{self.entry.total_images} images")
        self._count_lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")

        self._rec_btn = QPushButton("Recursive" if self.entry.recursive else "Top only")
        self._rec_btn.setCheckable(True)
        self._rec_btn.setChecked(self.entry.recursive)
        self._rec_btn.setFixedHeight(20)
        self._rec_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {COLORS['border_base']};
                border-radius: 4px;
                color: {COLORS['text_tertiary']};
                font-size: 10px;
                padding: 0 6px;
            }}
            QPushButton:checked {{
                border-color: {COLORS['accent_dim']};
                color: {COLORS['accent']};
            }}
        """)
        self._rec_btn.toggled.connect(self._on_recursive)

        bot.addWidget(self._count_lbl)
        bot.addStretch()
        bot.addWidget(self._rec_btn)
        lay.addLayout(bot)

    def _on_recursive(self, checked: bool) -> None:
        self._rec_btn.setText("Recursive" if checked else "Top only")
        self.recursive_toggled.emit(self.entry.path, checked)

    def update_count(self, n: int) -> None:
        self.entry.total_images = n
        self._count_lbl.setText(f"{n} images")

    def set_scanning(self, v: bool) -> None:
        self._scanning = v
        if v:
            self._count_lbl.setText("Scanning…")
            self._count_lbl.setStyleSheet(f"color: {COLORS['accent_dim']}; font-size: 11px;")
        else:
            self._count_lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
            self.update_count(self.entry.total_images)

    def _update_style(self, highlighted: bool) -> None:
        bg = COLORS['bg_hover'] if highlighted else COLORS['bg_surface']
        self.setStyleSheet(f"""
            #folderRow {{
                background: {bg};
                border: 1px solid {COLORS['border_base']};
                border-radius: 8px;
            }}
        """)


# ── Folders panel ─────────────────────────────────────────────────────────────

class FoldersPanel(QWidget):
    """Left sidebar — folder list management."""

    start_session_requested = Signal(list)   # list of ImageEntry

    def __init__(self, library: Library, parent=None) -> None:
        super().__init__(parent)
        self._lib      = library
        self._rows:    dict[str, FolderRow] = {}
        self.setAcceptDrops(True)
        self._build()
        self._connect_library()
        self._reload_rows()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setStyleSheet(f"background: {COLORS['bg_surface']}; border-bottom: 1px solid {COLORS['border_base']};")
        hlay = QHBoxLayout(hdr)
        hlay.setContentsMargins(16, 14, 16, 14)
        title = QLabel("LIBRARY")
        title.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px; font-weight: 700; letter-spacing: 1.5px;")
        hlay.addWidget(title)
        hlay.addStretch()

        add_btn = QPushButton("+ Add Folder")
        add_btn.setFixedHeight(28)
        add_btn.setProperty("class", "accent")
        add_btn.clicked.connect(self._add_folder)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #0A0A0B;
                border: none;
                border-radius: 5px;
                font-size: 12px;
                font-weight: 600;
                padding: 0 12px;
            }}
            QPushButton:hover {{ background: #D9BA8F; }}
        """)
        hlay.addWidget(add_btn)
        lay.addWidget(hdr)

        # Scroll area for folder rows
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._inner = QWidget()
        self._inner.setStyleSheet("background: transparent;")
        self._folders_lay = QVBoxLayout(self._inner)
        self._folders_lay.setContentsMargins(12, 12, 12, 12)
        self._folders_lay.setSpacing(6)
        self._folders_lay.addStretch()
        self._scroll.setWidget(self._inner)
        lay.addWidget(self._scroll, 1)

        # Bottom stats bar
        stats = QWidget()
        stats.setStyleSheet(f"background: {COLORS['bg_surface']}; border-top: 1px solid {COLORS['border_base']};")
        slay = QHBoxLayout(stats)
        slay.setContentsMargins(16, 10, 16, 10)
        self._stat_lbl = QLabel("0 images")
        self._stat_lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
        slay.addWidget(self._stat_lbl)
        slay.addStretch()

        clear_btn = QPushButton("Clear All")
        clear_btn.setFixedHeight(24)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {COLORS['error']};
                color: {COLORS['error']};
                border-radius: 4px;
                font-size: 11px;
                padding: 0 8px;
            }}
            QPushButton:hover {{ background: #B85C5C22; }}
        """)
        clear_btn.clicked.connect(self._clear_all)
        slay.addWidget(clear_btn)
        lay.addWidget(stats)

    def _connect_library(self) -> None:
        self._lib.folder_added.connect(self._on_folder_added)
        self._lib.folder_removed.connect(self._on_folder_removed)
        self._lib.scan_started.connect(self._on_scan_started)
        self._lib.scan_finished.connect(self._on_scan_finished)
        self._lib.library_changed.connect(self._update_stats)

    def _reload_rows(self) -> None:
        for folder in self._lib.folders():
            self._add_row(folder)
        self._update_stats()

    def _add_row(self, entry: FolderEntry) -> None:
        if entry.path in self._rows:
            return
        row = FolderRow(entry)
        row.remove_clicked.connect(self._remove_folder)
        row.refresh_clicked.connect(self._lib.scan_folder)
        row.recursive_toggled.connect(self._lib.set_recursive)
        self._rows[entry.path] = row
        # Insert before the stretch
        count = self._folders_lay.count()
        self._folders_lay.insertWidget(count - 1, row)

    def _on_folder_added(self, entry: FolderEntry) -> None:
        self._add_row(entry)
        self._update_stats()

    def _on_folder_removed(self, path: str) -> None:
        if path in self._rows:
            row = self._rows.pop(path)
            row.setParent(None)
        self._update_stats()

    def _on_scan_started(self, path: str) -> None:
        if path in self._rows:
            self._rows[path].set_scanning(True)

    def _on_scan_finished(self, path: str, total: int) -> None:
        if path in self._rows:
            self._rows[path].set_scanning(False)
            self._rows[path].update_count(total)

    def _update_stats(self) -> None:
        n = self._lib.image_count()
        f = self._lib.folder_count()
        self._stat_lbl.setText(f"{n:,} images · {f} folders")

    def _add_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select Image Folder", str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if path:
            self._lib.add_folder(path)

    def _remove_folder(self, path: str) -> None:
        self._lib.remove_folder(path)

    def _clear_all(self) -> None:
        self._lib.clear_all()
        for row in list(self._rows.values()):
            row.setParent(None)
        self._rows.clear()
        self._update_stats()

    # ── drag-and-drop ─────────────────────────────────────────────────────────

    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent) -> None:
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self._lib.add_folder(path)
                Toast(self, f"Added: {Path(path).name}")


# ── Browser panel (right side) ────────────────────────────────────────────────

class BrowserPanel(QWidget):
    """Right panel — search bar, filters, thumbnail grid, action bar."""

    start_with_selected = Signal(list)   # list[ImageEntry]

    def __init__(self, library: Library, parent=None) -> None:
        super().__init__(parent)
        self._lib = library
        self._all_entries: list[ImageEntry] = []
        self._settings = get_settings()
        self._build()
        self._connect()
        self._refresh()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Toolbar ──
        toolbar = QWidget()
        toolbar.setStyleSheet(f"background: {COLORS['bg_surface']}; border-bottom: 1px solid {COLORS['border_base']};")
        tlay = QHBoxLayout(toolbar)
        tlay.setContentsMargins(12, 10, 12, 10)
        tlay.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by filename…")
        self._search.setFixedHeight(32)
        self._search.textChanged.connect(self._on_search)

        self._orient_cb = QComboBox()
        self._orient_cb.addItems(["Any", "Portrait", "Landscape"])
        self._orient_cb.setFixedHeight(32)
        self._orient_cb.currentIndexChanged.connect(self._refresh)

        self._quality_cb = QComboBox()
        self._quality_cb.addItems(["Low", "Medium", "High"])
        self._quality_cb.setCurrentIndex(1)
        self._quality_cb.setFixedHeight(32)
        self._quality_cb.currentIndexChanged.connect(self._on_quality)

        col_lbl = QLabel("Cols:")
        col_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        self._col_cb = QComboBox()
        self._col_cb.addItems(["3", "4", "5", "6", "7", "8"])
        self._col_cb.setCurrentIndex(2)  # default 5
        self._col_cb.setFixedHeight(32)
        self._col_cb.setFixedWidth(55)
        self._col_cb.currentTextChanged.connect(
            lambda t: self._grid.set_columns(int(t))
        )

        tlay.addWidget(self._search, 2)
        tlay.addWidget(self._orient_cb)
        tlay.addWidget(self._quality_cb)
        tlay.addWidget(col_lbl)
        tlay.addWidget(self._col_cb)
        lay.addWidget(toolbar)

        # ── Grid ──
        self._grid = ThumbnailGrid(columns=5, quality="medium")
        self._grid.selection_changed.connect(self._on_selection)
        self._grid.image_activated.connect(self._on_image_activated)
        lay.addWidget(self._grid, 1)

        # ── Action bar ──
        abar = QWidget()
        abar.setStyleSheet(f"background: {COLORS['bg_surface']}; border-top: 1px solid {COLORS['border_base']};")
        alay = QHBoxLayout(abar)
        alay.setContentsMargins(12, 8, 12, 8)
        alay.setSpacing(10)

        self._count_lbl = QLabel("0 images")
        self._count_lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")

        self._sel_lbl = PillBadge("0 selected")

        sel_all_btn = QPushButton("Select All")
        sel_all_btn.setFixedHeight(28)
        sel_all_btn.clicked.connect(self._grid.select_all)

        clr_btn = QPushButton("Clear")
        clr_btn.setFixedHeight(28)
        clr_btn.clicked.connect(self._grid.clear_selection)

        self._start_sel_btn = QPushButton("▶  Start with Selected")
        self._start_sel_btn.setFixedHeight(32)
        self._start_sel_btn.setEnabled(False)
        self._start_sel_btn.setProperty("class", "accent")
        self._start_sel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #0A0A0B;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                padding: 0 16px;
            }}
            QPushButton:hover {{ background: #D9BA8F; }}
            QPushButton:disabled {{ background: {COLORS['bg_elevated']}; color: {COLORS['text_tertiary']}; }}
        """)
        self._start_sel_btn.clicked.connect(
            lambda: self.start_with_selected.emit(self._grid.selected_entries())
        )

        alay.addWidget(self._count_lbl)
        alay.addWidget(self._sel_lbl)
        alay.addStretch()
        alay.addWidget(sel_all_btn)
        alay.addWidget(clr_btn)
        alay.addWidget(self._start_sel_btn)
        lay.addWidget(abar)

    def _connect(self) -> None:
        self._lib.library_changed.connect(self._refresh)

    def _refresh(self) -> None:
        orient = self._orient_cb.currentText().lower()
        if orient == "any":
            entries = self._lib.all_images("any")
        else:
            entries = self._lib.all_images(orient)

        query = self._search.text().strip()
        if query:
            q = query.lower()
            entries = [e for e in entries if q in e.filename.lower()]

        self._all_entries = entries
        self._grid.set_entries(entries)
        self._count_lbl.setText(f"{len(entries):,} images")

    def _on_search(self) -> None:
        QTimer.singleShot(200, self._refresh)

    def _on_quality(self) -> None:
        q = self._quality_cb.currentText().lower()
        self._grid.set_quality(q)

    def _on_selection(self, selected: list) -> None:
        n = len(selected)
        self._sel_lbl.setText(f"{n} selected")
        self._start_sel_btn.setEnabled(n > 0)

    def _on_image_activated(self, entry: ImageEntry) -> None:
        # Double-click starts a session with just this image (goes to config)
        self.start_with_selected.emit([entry])


# ── Combined Library View ─────────────────────────────────────────────────────

class LibraryView(QWidget):
    """
    Full library tab: folder panel (left) + browser (right)
    separated by a draggable splitter.
    """
    start_session_requested = Signal(list)   # list[ImageEntry] or empty (all)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._lib = get_library()
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {COLORS['border_base']}; }}")

        self._folders_panel = FoldersPanel(self._lib)
        self._folders_panel.setMinimumWidth(220)
        self._folders_panel.setMaximumWidth(320)

        self._browser = BrowserPanel(self._lib)
        self._browser.start_with_selected.connect(self.start_session_requested)

        splitter.addWidget(self._folders_panel)
        splitter.addWidget(self._browser)
        splitter.setSizes([260, 740])

        lay.addWidget(splitter)

    def library(self) -> Library:
        return self._lib
