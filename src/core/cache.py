"""
Poscure Cache — SQLite-backed thumbnail & image metadata store.
"""

from __future__ import annotations
import hashlib, io, os, sqlite3, threading
from pathlib import Path
from typing import Optional
from PIL import Image


def _cache_dir() -> Path:
    import sys
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    d = base / "Poscure" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


CACHE_DIR = _cache_dir()
DB_PATH   = CACHE_DIR / "thumbnails.db"

THUMB_SIZES = {"low": (120, 120), "medium": (200, 200), "high": (320, 320)}

SCHEMA = """
CREATE TABLE IF NOT EXISTS thumbnails (
    path TEXT NOT NULL, mtime REAL NOT NULL, file_size INTEGER NOT NULL,
    quality TEXT NOT NULL, width INTEGER, height INTEGER, thumb_data BLOB NOT NULL,
    PRIMARY KEY (path, quality)
);
CREATE TABLE IF NOT EXISTS image_hashes (
    path TEXT PRIMARY KEY, mtime REAL NOT NULL,
    file_size INTEGER NOT NULL, file_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hash ON image_hashes(file_hash);
"""


class ThumbnailCache:
    def __init__(self) -> None:
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self) -> None:
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()

    def _is_valid(self, conn, path, quality, stat) -> bool:
        row = conn.execute(
            "SELECT mtime, file_size FROM thumbnails WHERE path=? AND quality=?",
            (path, quality)).fetchone()
        return bool(row and abs(row[0] - stat.st_mtime) < 0.01 and row[1] == stat.st_size)

    def get_thumbnail(self, path: str | Path, quality: str = "medium") -> Optional[bytes]:
        path = str(path)
        try:
            stat = os.stat(path)
        except OSError:
            return None
        conn = self._conn()
        if self._is_valid(conn, path, quality, stat):
            row = conn.execute(
                "SELECT thumb_data FROM thumbnails WHERE path=? AND quality=?",
                (path, quality)).fetchone()
            return row[0] if row else None
        return None

    def set_thumbnail(self, path: str | Path, quality: str, thumb_bytes: bytes,
                      width: int, height: int) -> None:
        path = str(path)
        try:
            stat = os.stat(path)
        except OSError:
            return
        conn = self._conn()
        conn.execute(
            "INSERT OR REPLACE INTO thumbnails "
            "(path,mtime,file_size,quality,width,height,thumb_data) VALUES (?,?,?,?,?,?,?)",
            (path, stat.st_mtime, stat.st_size, quality, width, height, thumb_bytes))
        conn.commit()

    def generate_thumbnail(self, path: str | Path, quality: str = "medium") -> Optional[bytes]:
        cached = self.get_thumbnail(path, quality)
        if cached:
            return cached
        size = THUMB_SIZES.get(quality, THUMB_SIZES["medium"])
        try:
            with Image.open(str(path)) as img:
                w, h = img.size
                img = img.convert("RGBA" if img.mode in ("RGBA","P") else "RGB")
                img.thumbnail(size, Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                data = buf.getvalue()
            self.set_thumbnail(path, quality, data, w, h)
            return data
        except Exception as e:
            print(f"[Cache] Thumbnail failed {path}: {e}")
            return None

    def get_file_hash(self, path: str | Path) -> Optional[str]:
        path = str(path)
        try:
            stat = os.stat(path)
        except OSError:
            return None
        conn = self._conn()
        row = conn.execute(
            "SELECT mtime,file_size,file_hash FROM image_hashes WHERE path=?",
            (path,)).fetchone()
        if row and abs(row[0]-stat.st_mtime) < 0.01 and row[1] == stat.st_size:
            return row[2]
        try:
            h = hashlib.md5()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            digest = h.hexdigest()
            conn.execute(
                "INSERT OR REPLACE INTO image_hashes (path,mtime,file_size,file_hash) VALUES (?,?,?,?)",
                (path, stat.st_mtime, stat.st_size, digest))
            conn.commit()
            return digest
        except Exception as e:
            print(f"[Cache] Hash failed {path}: {e}")
            return None

    def find_duplicates(self, paths: list[str]) -> dict[str, list[str]]:
        hm: dict[str, list[str]] = {}
        for p in paths:
            h = self.get_file_hash(p)
            if h:
                hm.setdefault(h, []).append(p)
        return {h: ps for h, ps in hm.items() if len(ps) > 1}

    def purge_missing(self) -> int:
        conn = self._conn()
        rows = conn.execute("SELECT DISTINCT path FROM thumbnails").fetchall()
        removed = 0
        for (p,) in rows:
            if not os.path.exists(p):
                conn.execute("DELETE FROM thumbnails WHERE path=?", (p,))
                conn.execute("DELETE FROM image_hashes WHERE path=?", (p,))
                removed += 1
        conn.commit()
        return removed

    def clear_all(self) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM thumbnails")
        conn.execute("DELETE FROM image_hashes")
        conn.commit()

    def stats(self) -> dict:
        conn = self._conn()
        return {
            "thumbnails":    conn.execute("SELECT COUNT(*) FROM thumbnails").fetchone()[0],
            "hashed_files":  conn.execute("SELECT COUNT(*) FROM image_hashes").fetchone()[0],
            "db_size_mb":    round(DB_PATH.stat().st_size / 1_048_576, 2) if DB_PATH.exists() else 0,
        }


_cache_instance: ThumbnailCache | None = None

def get_cache() -> ThumbnailCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ThumbnailCache()
    return _cache_instance
