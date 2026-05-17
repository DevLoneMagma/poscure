<div align="center">

<!-- Animated logo SVG -->
<img src="https://raw.githubusercontent.com/lonemagma/poscure/main/assets/logo.svg" alt="Poscure" width="96" height="96">

<br/>

# Poscure

**Draw more. Think less.**

A minimalist desktop app for gesture drawing and figure study practice.<br/>
Load your references, set a timer, and get into the flow — no distractions.

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-C8A97E?style=flat-square&labelColor=1F1F25)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows_%7C_Linux-9896A0?style=flat-square&labelColor=1F1F25)](https://github.com/lonemagma/poscure/releases)
[![Python](https://img.shields.io/badge/Python-3.10+-9896A0?style=flat-square&labelColor=1F1F25&logo=python&logoColor=C8A97E)](https://python.org)
[![Release](https://img.shields.io/github/v/release/lonemagma/poscure?style=flat-square&color=C8A97E&labelColor=1F1F25&label=Latest)](https://github.com/lonemagma/poscure/releases)

<br/>

[**Download for Windows**](https://github.com/lonemagma/poscure/releases/download/v1.0.0/Poscure.exe) · [Linux install guide](#-linux--source) · [Website](https://poscure.vercel.app)

<br/>

<!-- Hero SVG — animated app window mockup -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/lonemagma/poscure/main/assets/preview-dark.svg">
  <img src="https://raw.githubusercontent.com/lonemagma/poscure/main/assets/preview-dark.svg" alt="Poscure app preview" width="800">
</picture>

</div>

---

## What is Poscure?

Poscure is a **timed reference practice tool** for artists. It's built around one idea: get out of your way.

You add folders of reference images. You pick a duration. Poscure runs a fullscreen slideshow — no UI clutter, no ads, no cloud, nothing to log in to. When the timer runs out, the next image appears. You draw.

It's for gesture drawing (30s–60s sprints), figure study (2–10min), anatomy practice, or any timed reference work where the tool should disappear and let you focus.

---

## Features

- **Unlimited local folders** — recursive scanning, orientation filter, filename search
- **Timed sessions** — fixed or random duration per image (5 seconds to 10 minutes)
- **Quick presets** — 30s Gestures, 60s Gestures, 2min Studies, 5min Studies, Custom
- **Break system** — configurable rest interval every N images
- **Fullscreen mode** — controls auto-hide after 3 seconds, return on mouse move
- **Cross-fade transitions** — smooth image changes with animated arc countdown timer
- **Live transforms** — Mirror and Grayscale toggle instantly (no reload)
- **Previous image history** — ← goes back to the exact image shown, even in random mode
- **Session summary** — images shown + elapsed time at the end of every session
- **Hotkey-driven** — every action has a shortcut, all fully remappable
- **SQLite thumbnail cache** — fast startup even with 10,000+ image libraries
- **Drag-and-drop folders** — drag straight onto the sidebar
- **100% offline** — no accounts, no telemetry, no internet required

---

## Install

### Windows

Download the portable `.exe` from [Releases](https://github.com/lonemagma/poscure/releases). No installation. Single file, runs anywhere on Windows 10+.

> **SmartScreen warning?** Click **"More info" → "Run anyway"**. The app is unsigned because code-signing certificates cost $300/year. The source is fully open — read it before running if you prefer.

### Linux / Source

```bash
# 1. Clone
git clone https://github.com/lonemagma/poscure
cd poscure

# 2. Remove ghost directory (one-time fix from a known setup quirk)
rm -rf src/\{core,ui,widgets,utils\}

# 3. Set up environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Run
cd src && python main.py
```

**Requirements:** Python 3.10+ · PySide6 · Pillow · SQLite (stdlib)

### Build .exe from source (Windows)

```bash
pip install pyinstaller
pyinstaller poscure.spec
# → dist/Poscure.exe
```

Install [UPX](https://upx.github.io/) and add it to PATH before building for a smaller binary.

---

## Hotkeys

| Action | Key |
|---|---|
| Pause / Resume | `Space` |
| Next image | `→` |
| Previous image | `←` |
| Toggle fullscreen | `F` |
| Toggle grayscale | `G` |
| Toggle mirror | `M` |
| Show/hide timer | `T` |
| End session | `Esc` |
| Open settings | `Ctrl+S` |

All shortcuts are remappable in **Settings → Hotkeys**.

---

## Project Structure

```
poscure/
├── src/
│   ├── main.py                   Entry point
│   ├── core/
│   │   ├── library.py            Folder scanning, image indexing
│   │   ├── cache.py              SQLite thumbnail cache
│   │   ├── session.py            Session state machine + timer
│   │   └── settings.py           JSON config persistence
│   ├── ui/
│   │   ├── main_window.py        Root window, navigation controller
│   │   ├── library_view.py       Folder panel + browser grid
│   │   ├── session_config.py     Pre-session setup screen
│   │   ├── session_window.py     Fullscreen drawing session
│   │   ├── settings_panel.py     Settings dialog
│   │   ├── about_dialog.py       About / disclosure screen
│   │   └── theme.py              Design tokens + global stylesheet
│   ├── widgets/
│   │   ├── shared.py             Cards, toasts, rings, icon buttons
│   │   ├── thumbnail_grid.py     Lazy-loading grid with multi-select
│   │   ├── timer_widget.py       Animated arc countdown
│   │   └── toolbar_overlay.py    Auto-hiding session toolbar
│   └── utils/
│       ├── image_utils.py        Pillow transforms, loading
│       └── hotkeys.py            QShortcut registry
├── poscure.spec                  PyInstaller build config
├── requirements.txt
├── LICENSE
└── README.md
```

**Tech stack:** Python · PySide6 (Qt6) · Pillow · SQLite · PyInstaller

---

## v2 Roadmap

Planned after real-world feedback from v1 testers:

- [ ] Session history & statistics
- [ ] Image tagging and favorites
- [ ] Zoom / pan during session
- [ ] Custom sound packs
- [ ] Multi-monitor support
- [ ] Proper cross-platform packaging (macOS)
- [ ] Shareable session presets

---

## Disclosure

Most of Poscure's codebase was written by **Claude** (Anthropic's AI), directed and architected by LoneMagma.

An architect doesn't lay every brick — the building is still theirs. AI handled implementation detail. Every decision about what to build, how it should feel, and what ships was human.

Tools used in development: Claude (Anthropic) · Claude.ai · Python · PySide6 · Pillow · SQLite

---

## Credits

Built by **[LoneMagma](https://instagram.com/lonemagma)** with ♥ — a **[Pacify](https://pacify.site)** project.

MIT licensed. See [LICENSE](LICENSE).

