"""Colored terminal output with isatty() detection and a small progress helper."""
from __future__ import annotations

import os
import sys
import time
from typing import Optional

_FORCE = os.environ.get("DBMIG_FORCE_COLOR") == "1"
_NO_COLOR = os.environ.get("NO_COLOR") is not None


def _use_color(stream) -> bool:
    if _NO_COLOR:
        return False
    if _FORCE:
        return True
    return hasattr(stream, "isatty") and stream.isatty()


def _c(code: str, text: str, stream=sys.stdout) -> str:
    if _use_color(stream):
        return f"\033[{code}m{text}\033[0m"
    return text


def ok(msg: str) -> None:
    print(f"{_c('32', '[ OK ]')} {msg}")


def warn(msg: str) -> None:
    print(f"{_c('33', '[WARN]')} {msg}")


def info(msg: str) -> None:
    print(f"{_c('36', '[INFO]')} {msg}")


def err(msg: str) -> None:
    print(f"{_c('31', '[FAIL]', sys.stderr)} {msg}", file=sys.stderr)


def heading(msg: str) -> None:
    print(_c("1;37", f"\n=== {msg} ==="))


def human_int(n: Optional[int]) -> str:
    if n is None or n < 0:
        return "?"
    return f"{n:,}"


def human_duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m"


class Progress:
    """Single-line live progress for a table copy (rows/sec + ETA)."""

    def __init__(self, label: str, total: Optional[int]) -> None:
        self.label = label
        self.total = total if (total and total > 0) else None
        self.done = 0
        self.start = time.time()
        self._last_render = 0.0
        self._enabled = _use_color(sys.stdout) or sys.stdout.isatty()

    def advance(self, n: int) -> None:
        self.done += n
        now = time.time()
        if now - self._last_render >= 0.25:
            self._render(now)
            self._last_render = now

    def _render(self, now: float) -> None:
        elapsed = max(now - self.start, 1e-6)
        rate = self.done / elapsed
        if self.total:
            pct = 100.0 * self.done / self.total
            remaining = (self.total - self.done) / rate if rate > 0 else 0
            line = (f"  {self.label}: {self.done:,}/{self.total:,} "
                    f"({pct:5.1f}%) {rate:,.0f} rows/s ETA {human_duration(remaining)}")
        else:
            line = f"  {self.label}: {self.done:,} rows {rate:,.0f} rows/s"
        if self._enabled:
            sys.stdout.write("\r" + line + " " * 8)
            sys.stdout.flush()
        # when not a tty, stay quiet until done()

    def done_(self) -> None:
        now = time.time()
        elapsed = max(now - self.start, 1e-6)
        rate = self.done / elapsed
        line = (f"  {self.label}: {self.done:,} rows in "
                f"{human_duration(elapsed)} ({rate:,.0f} rows/s)")
        if self._enabled:
            sys.stdout.write("\r" + line + " " * 16 + "\n")
            sys.stdout.flush()
        else:
            print(line)
