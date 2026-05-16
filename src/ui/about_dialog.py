"""
Poscure About Dialog — with full honest disclosure.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFrame, QScrollArea, QTabWidget
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from ui.theme import COLORS


def _link_btn(text: str, url: str, accent: bool = False) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(30)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if accent:
        btn.setStyleSheet(f"""
            QPushButton {{background:{COLORS['accent']};color:#0A0A0B;border:none;
            border-radius:5px;font-size:12px;font-weight:600;padding:0 12px;}}
            QPushButton:hover {{background:#D9BA8F;}}
        """)
    else:
        btn.setStyleSheet(f"""
            QPushButton {{background:{COLORS['bg_elevated']};border:1px solid {COLORS['border_base']};
            color:{COLORS['accent']};border-radius:5px;font-size:12px;padding:0 12px;}}
            QPushButton:hover {{background:{COLORS['bg_hover']};border-color:{COLORS['accent_dim']};}}
        """)
    btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
    return btn


def _divider() -> QFrame:
    d = QFrame()
    d.setFixedHeight(1)
    d.setStyleSheet(f"background:{COLORS['border_base']};border:none;")
    return d


def _para(text: str, color: str = None, size: int = 13, center: bool = False,
          italic: bool = False) -> QLabel:
    lbl = QLabel(text)
    c = color or COLORS['text_secondary']
    style = f"color:{c};font-size:{size}px;background:transparent;border:none;"
    if italic:
        style += "font-style:italic;"
    lbl.setStyleSheet(style)
    lbl.setWordWrap(True)
    if center:
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About Poscure")
        self.setMinimumSize(480, 600)
        self.setStyleSheet(f"background:{COLORS['bg_base']};color:{COLORS['text_primary']};")
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Hero header ──────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(190)
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {COLORS['bg_elevated']}, stop:1 {COLORS['bg_surface']});
            border-bottom:1px solid {COLORS['border_base']};
        """)
        hlay = QVBoxLayout(header)
        hlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hlay.setSpacing(6)

        logo = _para("◈", COLORS['accent'], 52, center=True)
        name = QLabel("Poscure")
        name.setStyleSheet(f"""
            font-size:26px;font-weight:700;color:{COLORS['text_primary']};
            letter-spacing:1.5px;background:transparent;
        """)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tagline = _para("References. Flow. No distractions.", None, 13, center=True, italic=True)
        version = _para("Version 1.0.0", COLORS['text_tertiary'], 11, center=True)

        hlay.addWidget(logo)
        hlay.addWidget(name)
        hlay.addWidget(tagline)
        hlay.addWidget(version)
        root.addWidget(header)

        # ── Tabbed body ───────────────────────────────────────────────────────
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{border:none;background:{COLORS['bg_base']};}}
            QTabBar::tab {{background:transparent;color:{COLORS['text_secondary']};
                padding:9px 18px;border:none;border-bottom:2px solid transparent;font-size:12px;}}
            QTabBar::tab:selected {{color:{COLORS['text_primary']};
                border-bottom:2px solid {COLORS['accent']};}}
            QTabBar::tab:hover {{color:{COLORS['text_primary']};}}
        """)

        tabs.addTab(self._tab_about(),       "About")
        tabs.addTab(self._tab_disclosure(),  "Disclosure")
        tabs.addTab(self._tab_credits(),     "Credits")

        root.addWidget(tabs, 1)

        # ── Footer ────────────────────────────────────────────────────────────
        footer = QWidget()
        footer.setFixedHeight(56)
        footer.setStyleSheet(f"background:{COLORS['bg_surface']};border-top:1px solid {COLORS['border_base']};")
        flay = QHBoxLayout(footer)
        flay.setContentsMargins(20, 0, 20, 0)
        flay.setSpacing(10)

        flay.addWidget(_link_btn("poscure.vercel.app  ↗", "https://poscure.vercel.app", accent=True))
        flay.addStretch()

        close = QPushButton("Close")
        close.setFixedSize(90, 32)
        close.setStyleSheet(f"""
            QPushButton {{background:{COLORS['bg_elevated']};border:1px solid {COLORS['border_base']};
            color:{COLORS['text_secondary']};border-radius:6px;font-size:13px;}}
            QPushButton:hover {{color:{COLORS['text_primary']};background:{COLORS['bg_hover']};}}
        """)
        close.clicked.connect(self.accept)
        flay.addWidget(close)
        root.addWidget(footer)

    # ── Tab: About ────────────────────────────────────────────────────────────

    def _tab_about(self) -> QWidget:
        w, lay = self._scroll_tab()

        lay.addWidget(_para(
            "Poscure is a minimalist desktop app for gesture drawing and figure study practice. "
            "Load your own image references, configure timed sessions, and get into the flow "
            "with zero distractions.",
            size=13
        ))
        lay.addSpacing(8)
        lay.addWidget(_divider())
        lay.addSpacing(8)

        lay.addWidget(_para("Features", COLORS['text_primary'], 13))
        for feat in [
            "Local image libraries — unlimited folders, recursive scanning",
            "Lazy-loading thumbnail grid with search and orientation filter",
            "Timed sessions: fixed or random duration per image (5s – 600s)",
            "Random, sequential, and shuffle-once ordering",
            "Break system — configurable rest every N images",
            "Mirror and Grayscale transforms (instant, no reload)",
            "Cross-fade image transitions with animated arc timer",
            "Previous image history stack (works in random mode)",
            "Session summary screen",
            "Fully customizable hotkeys",
            "Persistent settings — remembers everything between launches",
            "SQLite thumbnail cache for fast restarts",
            "100% offline — no accounts, no internet, no telemetry",
        ]:
            row = QHBoxLayout()
            dot = _para("·", COLORS['accent'], 13)
            dot.setFixedWidth(14)
            row.addWidget(dot)
            row.addWidget(_para(feat, size=13), 1)
            container = QWidget()
            container.setStyleSheet("background:transparent;")
            container.setLayout(row)
            lay.addWidget(container)

        lay.addStretch()
        return w

    # ── Tab: Disclosure ───────────────────────────────────────────────────────

    def _tab_disclosure(self) -> QWidget:
        w, lay = self._scroll_tab()

        lay.addWidget(_para("How Poscure was built", COLORS['text_primary'], 14))
        lay.addSpacing(6)

        lay.addWidget(_para(
            "The majority of Poscure's codebase was written by Claude — Anthropic's AI — "
            "directed and architected by LoneMagma.",
            size=13
        ))
        lay.addSpacing(10)

        # The analogy block
        quote = QFrame()
        quote.setStyleSheet(f"""
            background:{COLORS['bg_elevated']};
            border-left:3px solid {COLORS['accent']};
            border-radius:0px;
            padding:0px;
        """)
        qlay = QVBoxLayout(quote)
        qlay.setContentsMargins(14, 12, 14, 12)
        qlay.addWidget(_para(
            "An architect doesn't lay every brick. They design, direct, and take responsibility "
            "for the outcome — the building is still fully theirs.",
            COLORS['text_secondary'], 13, italic=True
        ))
        lay.addWidget(quote)
        lay.addSpacing(10)

        lay.addWidget(_para(
            "Using AI to write code isn't cutting corners — it's working at a higher level of "
            "abstraction. The decisions about what to build, how it should feel, what the "
            "architecture looks like, and what gets shipped: those are entirely human. "
            "The AI handles the implementation detail.",
            size=13
        ))
        lay.addSpacing(8)
        lay.addWidget(_para(
            "This approach lets a single developer ship something that would normally take a team — "
            "without sacrificing quality, structure, or intent.",
            size=13
        ))
        lay.addSpacing(12)
        lay.addWidget(_divider())
        lay.addSpacing(12)

        lay.addWidget(_para("Tools used in development", COLORS['text_primary'], 13))
        lay.addSpacing(6)

        for tool, desc in [
            ("Claude (Anthropic)", "AI assistant — primary code generation, architecture, debugging"),
            ("Claude.ai",          "Web interface used for agentic development sessions"),
        ]:
            row_w = QWidget()
            row_w.setStyleSheet("background:transparent;")
            rlay = QHBoxLayout(row_w)
            rlay.setContentsMargins(0, 0, 0, 0)
            rlay.setSpacing(10)
            name_lbl = _para(tool, COLORS['text_primary'], 13)
            name_lbl.setFixedWidth(160)
            rlay.addWidget(name_lbl)
            rlay.addWidget(_para(desc, COLORS['text_tertiary'], 12), 1)
            lay.addWidget(row_w)

        lay.addStretch()
        return w

    # ── Tab: Credits ──────────────────────────────────────────────────────────

    def _tab_credits(self) -> QWidget:
        w, lay = self._scroll_tab()

        # Built by
        built_row = QHBoxLayout()
        built_row.setSpacing(8)
        built_lbl = _para("Built by", size=13)
        built_lbl.setFixedWidth(55)
        built_row.addWidget(built_lbl)
        built_row.addWidget(_link_btn("LoneMagma ↗", "https://instagram.com/lonemagma"))
        built_row.addWidget(_para("with  ♥", COLORS['accent'], 13))
        built_row.addStretch()
        bw = QWidget()
        bw.setStyleSheet("background:transparent;")
        bw.setLayout(built_row)
        lay.addWidget(bw)
        lay.addSpacing(4)

        proj_row = QHBoxLayout()
        proj_row.setSpacing(8)
        proj_lbl = _para("A", size=13)
        proj_lbl.setFixedWidth(14)
        proj_row.addWidget(proj_lbl)
        proj_row.addWidget(_link_btn("Pacify  ↗", "https://pacify.site"))
        proj_row.addWidget(_para("project", size=13))
        proj_row.addStretch()
        pw = QWidget()
        pw.setStyleSheet("background:transparent;")
        pw.setLayout(proj_row)
        lay.addWidget(pw)

        lay.addSpacing(16)
        lay.addWidget(_divider())
        lay.addSpacing(16)

        lay.addWidget(_para("Open source technologies", COLORS['text_primary'], 13))
        lay.addSpacing(8)

        for lib, purpose in [
            ("Python 3.11+",      "Core language"),
            ("PySide6 (Qt6)",     "UI framework — windows, widgets, rendering"),
            ("Pillow",            "Image loading, thumbnails, transforms"),
            ("SQLite",            "Thumbnail & metadata cache (stdlib)"),
            ("PyInstaller",       "Portable .exe packaging"),
        ]:
            row_w = QWidget()
            row_w.setStyleSheet("background:transparent;")
            rlay = QHBoxLayout(row_w)
            rlay.setContentsMargins(0, 2, 0, 2)
            rlay.setSpacing(10)
            n = _para(lib, COLORS['text_primary'], 13)
            n.setFixedWidth(160)
            rlay.addWidget(n)
            rlay.addWidget(_para(purpose, COLORS['text_tertiary'], 12), 1)
            lay.addWidget(row_w)

        lay.addStretch()
        return w

    # ── Util ──────────────────────────────────────────────────────────────────

    def _scroll_tab(self) -> tuple[QWidget, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setStyleSheet(f"background:{COLORS['bg_base']};")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(8)
        scroll.setWidget(inner)
        return scroll, lay
