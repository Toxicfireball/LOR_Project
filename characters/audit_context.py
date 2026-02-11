# characters/audit_context.py
import threading

_state = threading.local()


def set_current_request(user, path: str):
    _state.user = user
    _state.path = path or ""


def clear_current_request():
    _state.user = None
    _state.path = ""
    _state.before = {}


def get_current_user():
    return getattr(_state, "user", None)


def get_current_path():
    return getattr(_state, "path", "")


def set_before_snapshot(key, data: dict):
    if not hasattr(_state, "before"):
        _state.before = {}
    _state.before[key] = data


def pop_before_snapshot(key):
    before = getattr(_state, "before", {})
    return before.pop(key, None)
