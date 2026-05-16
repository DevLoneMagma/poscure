"""
Poscure Session — manages session state, image queue, timer logic.
Pure logic, no UI dependencies.
"""

from __future__ import annotations
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer

from core.library import ImageEntry


class SessionState(Enum):
    IDLE     = auto()
    RUNNING  = auto()
    PAUSED   = auto()
    BREAK    = auto()
    FINISHED = auto()


class OrderMode(Enum):
    RANDOM       = "random"
    SEQUENTIAL   = "sequential"
    SHUFFLE_ONCE = "shuffle_once"


@dataclass
class SessionConfig:
    images:           list[ImageEntry]
    duration:         int              = 30       # seconds per image
    duration_random:  bool             = False
    duration_min:     int              = 10
    duration_max:     int              = 45
    order:            OrderMode        = OrderMode.RANDOM
    image_count:      int | str        = "all"   # int or "all"
    break_enabled:    bool             = False
    break_every_n:    int              = 10
    break_duration:   int              = 30
    repeat:           bool             = False
    time_limit:       int              = 0        # 0 = no limit


@dataclass
class SessionStats:
    total_images:     int   = 0
    images_shown:     int   = 0
    start_time:       float = 0.0
    end_time:         float = 0.0
    paused_duration:  float = 0.0

    @property
    def elapsed(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time - self.paused_duration
        return time.time() - self.start_time - self.paused_duration


class Session(QObject):
    """
    Core session state machine.

    Signals:
        image_changed(ImageEntry, index, total)  — new image to show
        timer_tick(remaining_seconds)             — every second
        state_changed(SessionState)
        break_started(duration_seconds)
        break_tick(remaining)
        session_finished(SessionStats)
        image_change_requested()                  — audio cue hook
    """

    image_changed     = Signal(object, int, int)   # entry, idx, total
    timer_tick        = Signal(int)                 # remaining seconds
    state_changed     = Signal(object)              # SessionState
    break_started     = Signal(int)
    break_tick        = Signal(int)
    session_finished  = Signal(object)              # SessionStats
    image_change_requested = Signal()

    def __init__(self, config: SessionConfig) -> None:
        super().__init__()
        self.config  = config
        self.state   = SessionState.IDLE
        self.stats   = SessionStats(total_images=0)

        self._queue:       list[ImageEntry] = []
        self._history:     list[int]        = []   # history of queue indices
        self._history_pos: int              = -1   # position in history stack
        self._current_idx: int              = -1
        self._images_shown: int            = 0

        self._remaining:   int              = 0    # seconds left on current image
        self._break_remaining: int          = 0

        self._timer     = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        self._break_timer = QTimer(self)
        self._break_timer.setInterval(1000)
        self._break_timer.timeout.connect(self._on_break_tick)

        self._pause_start: float = 0.0
        self._session_limit_timer: Optional[QTimer] = None

        self._build_queue()

    # ── queue building ────────────────────────────────────────────────────────

    def _build_queue(self) -> None:
        imgs = list(self.config.images)

        # Apply image count limit
        if self.config.image_count != "all":
            n = int(self.config.image_count)
            imgs = imgs[:n]

        # Apply order
        mode = self.config.order
        if mode == OrderMode.RANDOM:
            pass  # shuffle per-step
        elif mode == OrderMode.SEQUENTIAL:
            pass  # keep as-is
        elif mode == OrderMode.SHUFFLE_ONCE:
            random.shuffle(imgs)

        self._queue = imgs
        self.stats.total_images = len(imgs)

    def _pick_next_index(self) -> Optional[int]:
        if not self._queue:
            return None
        if self.config.order == OrderMode.RANDOM:
            return random.randrange(len(self._queue))
        else:
            # Sequential / shuffle_once
            if self._current_idx + 1 >= len(self._queue):
                if self.config.repeat:
                    return 0
                return None
            return self._current_idx + 1

    # ── public controls ───────────────────────────────────────────────────────

    def start(self) -> None:
        if self.state not in (SessionState.IDLE,):
            return
        self.stats.start_time = time.time()
        self._set_state(SessionState.RUNNING)

        # Optional session time limit
        if self.config.time_limit > 0:
            self._session_limit_timer = QTimer(self)
            self._session_limit_timer.setSingleShot(True)
            self._session_limit_timer.setInterval(self.config.time_limit * 1000)
            self._session_limit_timer.timeout.connect(self._finish)
            self._session_limit_timer.start()

        self._advance(from_history=False)

    def pause(self) -> None:
        if self.state == SessionState.RUNNING:
            self._timer.stop()
            self._pause_start = time.time()
            self._set_state(SessionState.PAUSED)

    def resume(self) -> None:
        if self.state == SessionState.PAUSED:
            elapsed_paused = time.time() - self._pause_start
            self.stats.paused_duration += elapsed_paused
            self._set_state(SessionState.RUNNING)
            self._timer.start()

    def toggle_pause(self) -> None:
        if self.state == SessionState.RUNNING:
            self.pause()
        elif self.state == SessionState.PAUSED:
            self.resume()

    def next_image(self) -> None:
        """Advance to next image (manual override)."""
        if self.state in (SessionState.RUNNING, SessionState.PAUSED):
            was_paused = self.state == SessionState.PAUSED
            self._timer.stop()
            self._advance(from_history=False)
            if was_paused:
                self.pause()

    def previous_image(self) -> None:
        """Go back to previous image in history."""
        if self.state not in (SessionState.RUNNING, SessionState.PAUSED):
            return
        if self._history_pos <= 0:
            return
        was_paused = self.state == SessionState.PAUSED
        self._timer.stop()
        self._history_pos -= 1
        self._current_idx = self._history[self._history_pos]
        self._show_current()
        if was_paused:
            self.pause()
        else:
            self._timer.start()

    def end(self) -> None:
        self._finish()

    def current_entry(self) -> Optional[ImageEntry]:
        if 0 <= self._current_idx < len(self._queue):
            return self._queue[self._current_idx]
        return None

    @property
    def total(self) -> int:
        return len(self._queue)

    @property
    def position(self) -> int:
        """1-based position in session."""
        return self._images_shown

    # ── internal ──────────────────────────────────────────────────────────────

    def _set_state(self, state: SessionState) -> None:
        self.state = state
        self.state_changed.emit(state)

    def _advance(self, from_history: bool = False) -> None:
        """Move to next image, handling breaks and end conditions."""
        self._images_shown += 1
        self.stats.images_shown = self._images_shown

        # Check session completion
        if not from_history:
            # Check if we should insert a break
            if (self.config.break_enabled
                    and self._images_shown > 1
                    and (self._images_shown - 1) % self.config.break_every_n == 0):
                self._start_break()
                return

        idx = self._pick_next_index()
        if idx is None:
            if self.config.repeat:
                self._build_queue()
                self._current_idx = -1
                idx = self._pick_next_index()
                if idx is None:
                    self._finish()
                    return
            else:
                self._finish()
                return

        self._current_idx = idx

        # Push to history
        if self._history_pos < len(self._history) - 1:
            self._history = self._history[:self._history_pos + 1]
        self._history.append(idx)
        self._history_pos = len(self._history) - 1
        # Cap history to 100
        if len(self._history) > 100:
            self._history = self._history[-100:]
            self._history_pos = len(self._history) - 1

        self._show_current()

    def _show_current(self) -> None:
        entry = self.current_entry()
        if entry is None:
            return

        # Set timer duration
        if self.config.duration_random:
            self._remaining = random.randint(
                self.config.duration_min, self.config.duration_max
            )
        else:
            self._remaining = self.config.duration

        self.image_change_requested.emit()
        self.image_changed.emit(entry, self._images_shown, self.total)
        self.timer_tick.emit(self._remaining)
        self._timer.start()

    def _on_tick(self) -> None:
        self._remaining -= 1
        self.timer_tick.emit(self._remaining)
        if self._remaining <= 0:
            self._timer.stop()
            self._advance(from_history=False)

    def _start_break(self) -> None:
        self._timer.stop()
        self._break_remaining = self.config.break_duration
        self._set_state(SessionState.BREAK)
        self.break_started.emit(self.config.break_duration)
        self._break_timer.start()

    def _on_break_tick(self) -> None:
        self._break_remaining -= 1
        self.break_tick.emit(self._break_remaining)
        if self._break_remaining <= 0:
            self._break_timer.stop()
            self._set_state(SessionState.RUNNING)
            self._advance(from_history=False)

    def _finish(self) -> None:
        self._timer.stop()
        self._break_timer.stop()
        if self._session_limit_timer:
            self._session_limit_timer.stop()
        self.stats.end_time = time.time()
        self._set_state(SessionState.FINISHED)
        self.session_finished.emit(self.stats)
