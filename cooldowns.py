"""cooldowns: per-user, per-command cooldowns that survive restarts.

saves are atomic (write a temp file, then swap it in), and a corrupt save file is
set aside instead of crashing the bot or being silently overwritten.
"""
import json
import os
import tempfile
import time


def format_remaining(seconds: float) -> str:
    """1h 5m, 4m 12s, 30s."""
    seconds = max(0, int(seconds))
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s or not parts:
        parts.append(f"{s}s")
    return " ".join(parts[:2])


class CooldownManager:
    def __init__(self, path: str = None, clock=time.time):
        self.path = path
        self.clock = clock
        self._data = {}  # {user_id: {command: expires_at}}
        if path:
            self._load()

    # ---- queries ----
    def remaining(self, user_id, command: str) -> float:
        expires = self._data.get(str(user_id), {}).get(command, 0)
        return max(0.0, expires - self.clock())

    def is_ready(self, user_id, command: str) -> bool:
        return self.remaining(user_id, command) == 0

    # ---- changes ----
    def start(self, user_id, command: str, seconds: float) -> None:
        self._data.setdefault(str(user_id), {})[command] = self.clock() + seconds
        self._save()

    def check_and_start(self, user_id, command: str, seconds: float):
        """returns (ok, seconds_left). starts the cooldown only if it was ready."""
        left = self.remaining(user_id, command)
        if left > 0:
            return False, left
        self.start(user_id, command, seconds)
        return True, 0.0

    def reset(self, user_id, *commands: str) -> None:
        """clear specific cooldowns, or all of them if none are given."""
        user = self._data.get(str(user_id), {})
        for command in (commands or list(user)):
            user.pop(command, None)
        self._save()

    # ---- storage ----
    def _prune(self) -> None:
        now = self.clock()
        for uid in list(self._data):
            self._data[uid] = {c: e for c, e in self._data[uid].items() if e > now}
            if not self._data[uid]:
                del self._data[uid]

    def _save(self) -> None:
        if not self.path:
            return
        self._prune()
        folder = os.path.dirname(os.path.abspath(self.path))
        fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                self._data = json.load(f)
            if not isinstance(self._data, dict):
                raise ValueError("unexpected format")
        except (ValueError, OSError):
            os.replace(self.path, self.path + ".corrupt")
            self._data = {}
