"""
Poscure image utilities — loading, transforms, format helpers.
All heavy operations go through Pillow; display uses QPixmap.
"""

from __future__ import annotations
import io
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def is_supported(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def load_pixmap(path: str | Path,
                grayscale: bool = False,
                mirror: bool = False) -> Optional[QPixmap]:
    """
    Load an image file, apply transforms, return QPixmap.
    Returns None on any error (corrupted file etc.).
    """
    try:
        with Image.open(str(path)) as img:
            # Preserve EXIF orientation
            img = ImageOps.exif_transpose(img)

            if mirror:
                img = ImageOps.mirror(img)

            if grayscale:
                img = img.convert("L").convert("RGB")
            else:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")

            return pil_to_pixmap(img)
    except Exception as e:
        print(f"[ImageUtils] Failed to load {path}: {e}")
        return None


def pil_to_pixmap(img: Image.Image) -> QPixmap:
    """Convert PIL Image to QPixmap efficiently."""
    if img.mode == "RGBA":
        fmt = QImage.Format.Format_RGBA8888
        data = img.tobytes("raw", "RGBA")
    else:
        img = img.convert("RGB")
        fmt = QImage.Format.Format_RGB888
        data = img.tobytes("raw", "RGB")

    qimg = QImage(data, img.width, img.height, fmt)
    return QPixmap.fromImage(qimg)


def apply_grayscale(pixmap: QPixmap) -> QPixmap:
    """Convert an existing QPixmap to grayscale without reloading from disk."""
    img = pixmap.toImage()
    gray = img.convertToFormat(QImage.Format.Format_Grayscale8)
    # Convert back to RGB so rendering is consistent
    rgb  = gray.convertToFormat(QImage.Format.Format_RGB888)
    return QPixmap.fromImage(rgb)


def apply_mirror(pixmap: QPixmap) -> QPixmap:
    """Horizontally flip an existing QPixmap."""
    img = pixmap.toImage().mirrored(horizontal=True, vertical=False)
    return QPixmap.fromImage(img)


def fit_pixmap(pixmap: QPixmap, target_w: int, target_h: int,
               mode: str = "fit") -> QPixmap:
    """
    Scale pixmap to target dimensions according to fit mode.
    mode: 'fit'      → letterbox (keep aspect, no crop)
          'fill'     → zoom + crop to fill
          'original' → no scaling
    """
    if mode == "original":
        return pixmap

    pw, ph = pixmap.width(), pixmap.height()
    if pw == 0 or ph == 0:
        return pixmap

    if mode == "fit":
        return pixmap.scaled(
            target_w, target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
    elif mode == "fill":
        return pixmap.scaled(
            target_w, target_h,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
    return pixmap


def thumbnail_from_bytes(data: bytes) -> Optional[QPixmap]:
    """Load a QPixmap from PNG bytes (from cache)."""
    try:
        pm = QPixmap()
        pm.loadFromData(data, "PNG")
        return pm if not pm.isNull() else None
    except Exception:
        return None


def human_size(n_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} TB"
