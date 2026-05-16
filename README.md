# Poscure v1.0

**References. Flow. No distractions.**

A premium minimalist Windows desktop application for gesture drawing, figure drawing, and timed reference practice.

---

## Features

- Load unlimited local image folders (JPG, PNG, WEBP, BMP)
- Recursive subfolder scanning with background threading
- Lazy-loading thumbnail grid with multi-select
- Fully configurable timed sessions (5s–600s per image)
- Random, sequential, and shuffle-once ordering
- Break system (insert rest breaks every N images)
- Fullscreen session with auto-hiding toolbar overlay
- Animated arc countdown timer with warning flash
- Mirror and Grayscale transforms (cached, instant)
- Cross-fade image transitions
- Previous image history stack (works in random mode)
- Session summary screen
- Persistent settings and library state
- SQLite thumbnail cache (mtime-invalidated, fast)
- Drag-and-drop folder support
- Fully customizable hotkeys
- Single portable `.exe` distribution

---

## Setup (Development)

### Requirements
- Python 3.11+
- Windows (v1 target); Linux/macOS mostly works but untested

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
cd src
python main.py
```

---

## Build (Portable .exe)

```bash
# Install PyInstaller (already in requirements.txt)
pip install pyinstaller

# Build
pyinstaller poscure.spec

# Output: dist/Poscure.exe
```

For a smaller binary, install [UPX](https://upx.github.io/) and ensure it's on PATH before building.

---

## Project Structure

```
poscure/
├── src/
│   ├── main.py                  # Entry point
│   ├── core/
│   │   ├── library.py           # Folder scanning, image indexing
│   │   ├── cache.py             # SQLite thumbnail cache
│   │   ├── session.py           # Session state machine + timer
│   │   └── settings.py          # JSON config persistence
│   ├── ui/
│   │   ├── main_window.py       # Root window, navigation controller
│   │   ├── library_view.py      # Folder panel + browser grid
│   │   ├── session_config.py    # Pre-session setup screen
│   │   ├── session_window.py    # Fullscreen drawing session
│   │   ├── settings_panel.py    # Settings dialog
│   │   ├── about_dialog.py      # About screen
│   │   └── theme.py             # Design tokens + global stylesheet
│   ├── widgets/
│   │   ├── shared.py            # Reusable widgets (cards, rings, toasts)
│   │   ├── thumbnail_grid.py    # Lazy-loading grid with multi-select
│   │   ├── timer_widget.py      # Animated arc countdown
│   │   └── toolbar_overlay.py   # Auto-hiding session toolbar
│   └── utils/
│       ├── image_utils.py       # Pillow transforms, loading
│       └── hotkeys.py           # QShortcut registry
├── poscure.spec                # PyInstaller build spec
└── requirements.txt
```

---

## Hotkeys (defaults)

| Action          | Key         |
|-----------------|-------------|
| Pause / Resume  | Space       |
| Next image      | →           |
| Previous image  | ←           |
| Fullscreen      | F           |
| Grayscale       | G           |
| Mirror          | M           |
| Toggle timer    | T           |
| End session     | Esc         |
| Open settings   | Ctrl+S      |

All hotkeys are customizable in Settings → Hotkeys.

---

## Credits

Built by **LoneMagma** with ❤  
[A Pacify Project]

- [instagram.com/lonemagma](https://instagram.com/lonemagma)  
- [pacify.site](https://pacify.site)

**Technologies:** Python · PySide6 (Qt6) · Pillow · SQLite · PyInstaller
