"""Thread-safe brute-force limiter for named-save auth (load/list) attempts.

Two axes: per target identity (escalating lockout) and per client IP (sliding
window). In-memory; resets on restart. See spec §10.
"""
from __future__ import annotations

import threading

_ESCALATION = [60.0, 120.0, 300.0, 900.0]   # seconds; index = failures past the threshold


class AuthLimiter:
    def __init__(self, per_identity_max: int = 5, per_ip_max: int = 20,
                 ip_window: float = 300.0):
        self._lock = threading.Lock()
        self._id: dict[str, list] = {}    # key -> [fail_count, locked_until]
        self._ip: dict[str, list] = {}    # ip  -> [failure timestamps]
        self._per_identity_max = per_identity_max
        self._per_ip_max = per_ip_max
        self._ip_window = ip_window

    def locked_for(self, key: str, ip: str, now: float) -> float:
        with self._lock:
            wait = 0.0
            rec = self._id.get(key)
            if rec and rec[1] > now:
                wait = max(wait, rec[1] - now)
            hits = [t for t in self._ip.get(ip, []) if t > now - self._ip_window]
            self._ip[ip] = hits
            if len(hits) >= self._per_ip_max:
                wait = max(wait, (hits[0] + self._ip_window) - now)
            return wait

    def record_failure(self, key: str, ip: str, now: float) -> None:
        with self._lock:
            rec = self._id.setdefault(key, [0, 0.0])
            rec[0] += 1
            over = rec[0] - self._per_identity_max
            if over >= 0:
                rec[1] = now + _ESCALATION[min(over, len(_ESCALATION) - 1)]
            self._ip.setdefault(ip, []).append(now)

    def record_success(self, key: str) -> None:
        with self._lock:
            self._id.pop(key, None)
