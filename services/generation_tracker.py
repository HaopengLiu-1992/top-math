"""
Module-level background generation tracker.

States: idle → running → done | error
"""
import threading
from typing import Any

_lock = threading.Lock()
_state: dict[str, Any] = {
    "status": "idle",   # idle | running | done | error
    "date_str": None,
    "error": None,
}


def start(date_str: str, fn, *args, **kwargs) -> bool:
    """Kick off fn(*args, **kwargs) in a daemon thread.

    Returns False if a generation is already running.
    """
    with _lock:
        if _state["status"] == "running":
            return False
        _state.update(status="running", date_str=date_str, error=None)

    def _run():
        try:
            fn(*args, **kwargs)
            with _lock:
                _state["status"] = "done"
        except Exception as exc:
            with _lock:
                _state.update(status="error", error=str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return True


def get() -> dict[str, Any]:
    with _lock:
        return dict(_state)


def reset():
    with _lock:
        _state.update(status="idle", date_str=None, error=None)
