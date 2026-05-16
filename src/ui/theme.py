"""
Poscure Design System — color tokens, stylesheet, shared UI helpers.
"""

from __future__ import annotations

# ── Color tokens ──────────────────────────────────────────────────────────────

COLORS = {
    # Backgrounds
    "bg_deep":     "#0A0A0B",   # deepest background
    "bg_base":     "#111113",   # main window bg
    "bg_surface":  "#18181C",   # cards, panels
    "bg_elevated": "#1F1F25",   # elevated elements
    "bg_hover":    "#26262E",   # hover state
    "bg_active":   "#2D2D38",   # active/pressed

    # Borders
    "border_dim":   "#1E1E26",
    "border_base":  "#28283A",
    "border_light": "#38384E",

    # Text
    "text_primary":   "#F0EEE8",  # near-white with warm tint
    "text_secondary": "#9896A0",  # muted
    "text_tertiary":  "#5C5A66",  # very muted

    # Accent (warm gold — LoneMagma brand feel)
    "accent":         "#C8A97E",
    "accent_dim":     "#8A6F4E",
    "accent_glow":    "#C8A97E44",

    # Status
    "success":  "#5A9E6F",
    "warning":  "#C8954A",
    "error":    "#B85C5C",

    # Session timer ring
    "ring_track": "#1E1E26",
    "ring_fill":  "#C8A97E",
}


def build_stylesheet(accent: str = "#C8A97E") -> str:
    c = {**COLORS, "accent": accent}

    return f"""
/* ── Global reset ──────────────────────────────────────── */
* {{
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
    color: {c['text_primary']};
    outline: none;
    border: none;
}}

QMainWindow, QDialog {{
    background-color: {c['bg_base']};
}}

QWidget {{
    background-color: transparent;
}}

/* ── Scrollbars ─────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {c['bg_surface']};
    width: 6px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {c['border_light']};
    border-radius: 3px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c['accent_dim']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {c['bg_surface']};
    height: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {c['border_light']};
    border-radius: 3px;
    min-width: 32px;
}}

/* ── QPushButton ─────────────────────────────────────────── */
QPushButton {{
    background-color: {c['bg_elevated']};
    color: {c['text_primary']};
    border: 1px solid {c['border_base']};
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {c['bg_hover']};
    border-color: {c['border_light']};
}}
QPushButton:pressed {{
    background-color: {c['bg_active']};
}}
QPushButton:disabled {{
    color: {c['text_tertiary']};
    border-color: {c['border_dim']};
}}

QPushButton[class="accent"] {{
    background-color: {c['accent']};
    color: #0A0A0B;
    border: none;
    font-weight: 600;
}}
QPushButton[class="accent"]:hover {{
    background-color: #D9BA8F;
}}
QPushButton[class="accent"]:pressed {{
    background-color: {c['accent_dim']};
    color: {c['text_primary']};
}}

QPushButton[class="ghost"] {{
    background-color: transparent;
    border-color: transparent;
    color: {c['text_secondary']};
}}
QPushButton[class="ghost"]:hover {{
    background-color: {c['bg_hover']};
    color: {c['text_primary']};
    border-color: {c['border_dim']};
}}

QPushButton[class="danger"] {{
    background-color: transparent;
    border-color: {c['error']};
    color: {c['error']};
}}
QPushButton[class="danger"]:hover {{
    background-color: #B85C5C22;
}}

/* ── QLineEdit ───────────────────────────────────────────── */
QLineEdit {{
    background-color: {c['bg_surface']};
    border: 1px solid {c['border_base']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {c['text_primary']};
    selection-background-color: {c['accent_dim']};
}}
QLineEdit:focus {{
    border-color: {c['accent_dim']};
}}
QLineEdit::placeholder {{
    color: {c['text_tertiary']};
}}

/* ── QComboBox ───────────────────────────────────────────── */
QComboBox {{
    background-color: {c['bg_surface']};
    border: 1px solid {c['border_base']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {c['text_primary']};
    min-width: 80px;
}}
QComboBox:hover {{
    border-color: {c['border_light']};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c['text_secondary']};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {c['bg_elevated']};
    border: 1px solid {c['border_light']};
    border-radius: 6px;
    selection-background-color: {c['bg_active']};
    color: {c['text_primary']};
    padding: 4px;
}}

/* ── QSpinBox ────────────────────────────────────────────── */
QSpinBox {{
    background-color: {c['bg_surface']};
    border: 1px solid {c['border_base']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {c['text_primary']};
}}
QSpinBox:focus {{
    border-color: {c['accent_dim']};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: {c['bg_elevated']};
    border: none;
    width: 18px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background: {c['bg_hover']};
}}
QSpinBox::up-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {c['text_secondary']};
}}
QSpinBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c['text_secondary']};
}}

/* ── QSlider ─────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    background: {c['bg_elevated']};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {c['accent']};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {c['accent']};
    border-radius: 2px;
}}

/* ── QCheckBox ───────────────────────────────────────────── */
QCheckBox {{
    spacing: 8px;
    color: {c['text_secondary']};
}}
QCheckBox:hover {{
    color: {c['text_primary']};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {c['border_light']};
    border-radius: 4px;
    background: {c['bg_surface']};
}}
QCheckBox::indicator:checked {{
    background: {c['accent']};
    border-color: {c['accent']};
}}

/* ── QRadioButton ────────────────────────────────────────── */
QRadioButton {{
    spacing: 8px;
    color: {c['text_secondary']};
}}
QRadioButton:hover {{
    color: {c['text_primary']};
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {c['border_light']};
    border-radius: 8px;
    background: {c['bg_surface']};
}}
QRadioButton::indicator:checked {{
    background: {c['accent']};
    border-color: {c['accent']};
}}

/* ── QLabel ──────────────────────────────────────────────── */
QLabel {{
    background: transparent;
}}
QLabel[class="heading"] {{
    font-size: 16px;
    font-weight: 600;
    color: {c['text_primary']};
    letter-spacing: 0.3px;
}}
QLabel[class="subheading"] {{
    font-size: 12px;
    color: {c['text_secondary']};
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}
QLabel[class="muted"] {{
    color: {c['text_tertiary']};
    font-size: 12px;
}}
QLabel[class="accent"] {{
    color: {c['accent']};
}}

/* ── QTabWidget ──────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {c['border_base']};
    border-radius: 8px;
    background: {c['bg_surface']};
    margin-top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {c['text_secondary']};
    padding: 8px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    color: {c['text_primary']};
    border-bottom: 2px solid {c['accent']};
}}
QTabBar::tab:hover {{
    color: {c['text_primary']};
    background: {c['bg_hover']};
}}

/* ── QSplitter ───────────────────────────────────────────── */
QSplitter::handle {{
    background: {c['border_dim']};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}

/* ── QToolTip ────────────────────────────────────────────── */
QToolTip {{
    background: {c['bg_elevated']};
    color: {c['text_primary']};
    border: 1px solid {c['border_light']};
    border-radius: 5px;
    padding: 4px 8px;
    font-size: 12px;
}}

/* ── QProgressBar ────────────────────────────────────────── */
QProgressBar {{
    background: {c['bg_surface']};
    border: none;
    border-radius: 2px;
    height: 3px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {c['accent']};
    border-radius: 2px;
}}

/* ── QScrollArea ─────────────────────────────────────────── */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* ── QGroupBox ───────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {c['border_base']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    color: {c['text_secondary']};
    font-size: 11px;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background: {c['bg_base']};
}}

/* ── QListWidget ─────────────────────────────────────────── */
QListWidget {{
    background: {c['bg_surface']};
    border: 1px solid {c['border_base']};
    border-radius: 8px;
    padding: 4px;
}}
QListWidget::item {{
    border-radius: 5px;
    padding: 6px 8px;
    color: {c['text_primary']};
}}
QListWidget::item:hover {{
    background: {c['bg_hover']};
}}
QListWidget::item:selected {{
    background: {c['bg_active']};
    color: {c['text_primary']};
}}

/* ── Divider ─────────────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {c['border_base']};
    max-height: 1px;
    background: {c['border_base']};
}}
"""
