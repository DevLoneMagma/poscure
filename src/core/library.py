"""
Poscure Library — folder management, recursive image scanning,
image metadata, and background scanning with Qt signals.

CRASH FIX: Threads now properly quit() + deleteLater() on scan finish.
Workers kept alive via strong refs. Signals use QueuedConnection.
"""

from __future__ import annotations
import os
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    QObject, Signal, QThread, QMutex, QMutexLocker, Qt
)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@dataclass
class ImageEntry:
    path: str
    filename: str
    ext: str
    file_size: int
    width: int = 0
    height: int = 0
    orientation: str = "unknown"

    @property
    def aspect(self) -> float:
        return (self.width / self.height) if self.height else 1.0

    def matches_orientation(self, filter_: str) -> bool:
        return filter_ == "any" or self.orientation == filter_

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ImageEntry":
        return cls(**d)


@dataclass
class FolderEntry:
    path: str
    recursive: bool = True
    total_images: int = 0
    last_scanned: float = 0.0
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FolderEntry":
        return cls(**d)


class ScanWorker(QObject):
    progress    = Signal(str, int)
    image_found = Signal(object)
    finished    = Signal(str, int)
    error       = Signal(str, str)

    def __init__(self, folder: FolderEntry) -> None:
        super().__init__()
        self.folder = folder
        self._stop  = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        folder_path = Path(self.folder.path)
        if not folder_path.exists():
            self.error.emit(self.folder.path, "Folder not found")
            return
        count = 0
        try:
            it = folder_path.rglob("*") if self.folder.recursive else folder_path.iterdir()
            for p in it:
                if self._stop:
                    break
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                    entry = _make_entry(p)
                    if entry:
                        self.image_found.emit(entry)
                        count += 1
                        if count % 50 == 0:
                            self.progress.emit(self.folder.path, count)
        except Exception as e:
            self.error.emit(self.folder.path, str(e))
            return
        self.finished.emit(self.folder.path, count)


def _make_entry(p: Path) -> Optional[ImageEntry]:
    try:
        stat = p.stat()
        entry = ImageEntry(path=str(p), filename=p.name,
                           ext=p.suffix.lower(), file_size=stat.st_size)
        try:
            from PIL import Image
            with Image.open(str(p)) as img:
                entry.width, entry.height = img.size
            entry.orientation = (
                "landscape" if entry.width > entry.height else
                "portrait"  if entry.height > entry.width else
                "square"
            )
        except Exception:
            pass
        return entry
    except Exception:
        return None


class Library(QObject):
    folder_added    = Signal(object)
    folder_removed  = Signal(str)
    scan_started    = Signal(str)
    scan_progress   = Signal(str, int)
    scan_finished   = Signal(str, int)
    scan_error      = Signal(str, str)
    library_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._folders: dict[str, FolderEntry]                = {}
        self._images:  dict[str, ImageEntry]                 = {}
        self._mutex    = QMutex()
        self._workers: dict[str, tuple[QThread, ScanWorker]] = {}
        self._load()

    @staticmethod
    def _lib_path() -> Path:
        import sys
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home()))
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME",
                                       str(Path.home() / ".config")))
        d = base / "Poscure"
        d.mkdir(parents=True, exist_ok=True)
        return d / "library.json"

    def _load(self) -> None:
        p = self._lib_path()
        if not p.exists():
            return
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            for fd in data.get("folders", []):
                self._folders[fd["path"]] = FolderEntry.from_dict(fd)
            for im in data.get("images", []):
                self._images[im["path"]] = ImageEntry.from_dict(im)
        except Exception as e:
            print(f"[Library] Load failed: {e}")

    def _save(self) -> None:
        try:
            with self._lib_path().open("w", encoding="utf-8") as f:
                json.dump({
                    "folders": [f.to_dict() for f in self._folders.values()],
                    "images":  [i.to_dict() for i in self._images.values()],
                }, f, indent=2)
        except Exception as e:
            print(f"[Library] Save failed: {e}")

    # ── folder management ─────────────────────────────────────────────────────

    def add_folder(self, path: str, recursive: bool = True) -> Optional[FolderEntry]:
        path = str(Path(path).resolve())
        if path in self._folders:
            return self._folders[path]
        if not os.path.isdir(path):
            return None
        fe = FolderEntry(path=path, recursive=recursive)
        self._folders[path] = fe
        self._save()
        self.folder_added.emit(fe)
        self.scan_folder(path)
        return fe

    def remove_folder(self, path: str) -> None:
        path = str(Path(path).resolve())
        self._stop_scan(path)
        self._folders.pop(path, None)
        with QMutexLocker(self._mutex):
            for k in [k for k in self._images if k.startswith(path)]:
                del self._images[k]
        self._save()
        self.folder_removed.emit(path)
        self.library_changed.emit()

    def set_recursive(self, path: str, recursive: bool) -> None:
        if path in self._folders:
            self._folders[path].recursive = recursive
            self._save()

    def folders(self) -> list[FolderEntry]:
        return list(self._folders.values())

    def folder_count(self) -> int:
        return len(self._folders)

    # ── image access ──────────────────────────────────────────────────────────

    def all_images(self, orientation: str = "any") -> list[ImageEntry]:
        with QMutexLocker(self._mutex):
            imgs = list(self._images.values())
        return [i for i in imgs if i.matches_orientation(orientation)]

    def image_count(self) -> int:
        with QMutexLocker(self._mutex):
            return len(self._images)

    def images_for_folder(self, folder_path: str) -> list[ImageEntry]:
        p = str(Path(folder_path).resolve())
        with QMutexLocker(self._mutex):
            return [i for i in self._images.values() if i.path.startswith(p)]

    def search(self, query: str, orientation: str = "any") -> list[ImageEntry]:
        q = query.lower()
        return [i for i in self.all_images(orientation) if q in i.filename.lower()]

    def get_image(self, path: str) -> Optional[ImageEntry]:
        return self._images.get(path)

    # ── scanning (CRASH-FIXED) ────────────────────────────────────────────────

    def scan_folder(self, path: str) -> None:
        path = str(Path(path).resolve())
        if path not in self._folders:
            return
        self._stop_scan(path)

        with QMutexLocker(self._mutex):
            for k in [k for k in self._images if k.startswith(path)]:
                del self._images[k]

        fe     = self._folders[path]
        worker = ScanWorker(fe)
        thread = QThread(self)          # parent=self: Qt owns the thread
        worker.moveToThread(thread)

        Q = Qt.ConnectionType.QueuedConnection
        worker.image_found.connect(self._on_image_found,   Q)
        worker.progress.connect(self.scan_progress,         Q)
        worker.finished.connect(self._on_scan_finished,    Q)
        worker.error.connect(self.scan_error,               Q)
        thread.started.connect(worker.run)

        # KEY FIX: quit thread when worker is done, then clean up
        worker.finished.connect(thread.quit, Q)
        worker.error.connect(lambda *_: thread.quit(), Q)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda p=path: self._cleanup_worker(p))

        self._workers[path] = (thread, worker)
        self.scan_started.emit(path)
        thread.start()

    def scan_all(self) -> None:
        for p in list(self._folders.keys()):
            self.scan_folder(p)

    def _stop_scan(self, path: str) -> None:
        if path in self._workers:
            thread, worker = self._workers.pop(path)
            worker.stop()
            thread.quit()
            thread.wait(2000)

    def _cleanup_worker(self, path: str) -> None:
        self._workers.pop(path, None)

    def _on_image_found(self, entry: ImageEntry) -> None:
        with QMutexLocker(self._mutex):
            self._images[entry.path] = entry
        self.library_changed.emit()

    def _on_scan_finished(self, path: str, total: int) -> None:
        import time
        if path in self._folders:
            self._folders[path].total_images = total
            self._folders[path].last_scanned = time.time()
        self._save()
        self.scan_finished.emit(path, total)
        self.library_changed.emit()

    def clear_all(self) -> None:
        for p in list(self._folders.keys()):
            self._stop_scan(p)
        self._folders.clear()
        with QMutexLocker(self._mutex):
            self._images.clear()
        self._save()
        self.library_changed.emit()

    def stats(self) -> dict:
        return {
            "folders":   len(self._folders),
            "images":    len(self._images),
            "portrait":  sum(1 for i in self._images.values() if i.orientation == "portrait"),
            "landscape": sum(1 for i in self._images.values() if i.orientation == "landscape"),
        }


_lib_instance: Library | None = None

def get_library() -> Library:
    global _lib_instance
    if _lib_instance is None:
        _lib_instance = Library()
    return _lib_instance
