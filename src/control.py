"""
control.py - Shared signals between the UI and the agent thread.

- stop_event:  set() to request a graceful stop; cleared before each new run.
- push_screenshot / pop_screenshot: pass live JPEG frames from the scraper
  thread to the SSE endpoint without blocking the scraper.
"""

import threading

# ── Stop signal ───────────────────────────────────────────────────────────────
stop_event = threading.Event()

# ── Live screenshot stream ────────────────────────────────────────────────────
_shot_lock = threading.Lock()
_latest_frame: str = ""          # base64-encoded JPEG string
_new_frame_event = threading.Event()


def push_screenshot(b64_jpeg: str) -> None:
    """Called from the scraper thread after each page navigation."""
    global _latest_frame
    with _shot_lock:
        _latest_frame = b64_jpeg
    _new_frame_event.set()


def pop_screenshot(timeout: float = 5.0) -> str | None:
    """
    Block until a new frame is ready (or timeout).
    Returns the base64 string, or None on timeout / no activity.
    """
    got_new = _new_frame_event.wait(timeout=timeout)
    _new_frame_event.clear()
    if not got_new:
        return None
    with _shot_lock:
        return _latest_frame


def clear_screenshot() -> None:
    global _latest_frame
    with _shot_lock:
        _latest_frame = ""
    _new_frame_event.clear()
