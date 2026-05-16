"""
Poscure Settings — persistent config via JSON.
Stored in $XDG_CONFIG_HOME/Poscure/config.json (Linux/macOS)
           %APPDATA%/Poscure/config.json         (Windows)
"""

from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import Any


def _config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    d = base / "Poscure"
    d.mkdir(parents=True, exist_ok=True)
    return d


CONFIG_PATH = _config_dir() / "config.json"

DEFAULTS: dict[str, Any] = {
    "version": "1.0.0",
    "start_maximized": False,
    "remember_folders": True,
    "auto_refresh_on_start": False,
    "accent_color": "#C8A97E",
    "thumbnail_quality": "medium",
    "thumbnail_columns": 5,
    "ui_scale": 1.0,
    "default_duration": 30,
    "default_order": "random",
    "default_image_count": "all",
    "default_fit_mode": "fit",
    "break_enabled": False,
    "break_every_n": 10,
    "break_duration": 30,
    "repeat_session": False,
    "session_time_limit": 0,
    "show_timer": True,
    "show_counter": True,
    "show_progress_bar": True,
    "show_filename": False,
    "timer_position": "top-right",
    "timer_size": "large",
    "audio_enabled": False,
    "audio_volume": 0.5,
    "preload_count": 3,
    "max_memory_mb": 400,
    "cache_thumbnails": True,
    "hotkeys": {
        "pause_resume": "Space",
        "next":         "Right",
        "previous":     "Left",
        "fullscreen":   "F",
        "grayscale":    "G",
        "mirror":       "M",
        "toggle_timer": "T",
        "end_session":  "Escape",
        "open_settings":"Ctrl+S",
    },
    "last_folders": [],
    "last_session_config": {},
    "window_geometry": None,
    "always_on_top": False,
}


class Settings:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if CONFIG_PATH.exists():
            try:
                with CONFIG_PATH.open("r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data = {**DEFAULTS, **saved}
                if "hotkeys" in saved:
                    self._data["hotkeys"] = {**DEFAULTS["hotkeys"], **saved["hotkeys"]}
            except Exception:
                self._data = dict(DEFAULTS)
        else:
            self._data = dict(DEFAULTS)

    def save(self) -> None:
        try:
            with CONFIG_PATH.open("w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Settings] Could not save: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def get_hotkey(self, action: str) -> str:
        return self._data["hotkeys"].get(action, "")

    def set_hotkey(self, action: str, key: str) -> None:
        self._data["hotkeys"][action] = key
        self.save()

    def reset_to_defaults(self) -> None:
        self._data = dict(DEFAULTS)
        self.save()

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        return key in self._data


_instance: Settings | None = None

def get_settings() -> Settings:
    global _instance
    if _instance is None:
        _instance = Settings()
    return _instance
