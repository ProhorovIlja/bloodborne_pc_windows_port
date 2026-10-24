"""V33 trustworthy, bounded public presence projection for a future website.

NOT a wire protocol, HTTP service, location tracker, game client hook, or a
source of authentication. Only an authenticated authoritative game server
adapter may call mark_server_alive() or observe(). Raw client JSON must not be
wired directly here. No live service is currently connected to this module.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import re

AREA_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
MAX_PEERS = 4096
MAX_AREAS = 64
MIN_PUBLIC_AREA_POPULATION = 3
MEMBER_TTL_S = 90.0
FRESH_SERVER_S = 35.0
UNAVAILABLE_SERVER_S = 150.0


@dataclass(frozen=True)
class Observation:
    """Authoritative server-side observation. account_key never goes to public JSON."""
    account_key: str
    area_key: str
    observed_s: float
    share_area: bool = False
    in_pvp: bool = False


class Presence:
    def __init__(self):
        self._by_account: dict[str, Observation] = {}
        self._last_server_s: float | None = None
        self._last_sweep_s = -math.inf

    @staticmethod
    def _valid_time(t: float) -> bool:
        return isinstance(t, (int, float)) and not isinstance(t, bool) and math.isfinite(t) and t >= 0

    def mark_server_alive(self, now_s: float) -> None:
        """Explicit server heartbeat, including when zero hunters are connected."""
        if not self._valid_time(now_s):
            raise ValueError("invalid server clock")
        if self._last_server_s is not None and now_s < self._last_server_s:
            raise ValueError("nonmonotonic server clock")
        self._last_server_s = float(now_s)

    def _sweep(self, now_s: float) -> None:
        if now_s < self._last_sweep_s or now_s - self._last_sweep_s < 10:
            return
        self._by_account = {
            k: v for k, v in self._by_account.items()
            if v.observed_s <= now_s and now_s-v.observed_s <= MEMBER_TTL_S
        }
        self._last_sweep_s = now_s

    def observe(self, obs: Observation, now_s: float) -> bool:
        """Insert a signed-in link's verified area. No public coordinates/IDs."""
        if not self._valid_time(now_s) or not self._valid_time(obs.observed_s):
            return False
        if obs.observed_s > now_s or now_s-obs.observed_s > MEMBER_TTL_S:
            return False
        if not isinstance(obs.account_key, str) or not (1 <= len(obs.account_key) <= 96):
            return False
        if not isinstance(obs.area_key, str) or not AREA_RE.fullmatch(obs.area_key):
            return False
        if type(obs.share_area) is not bool or type(obs.in_pvp) is not bool:
            return False
        if self._last_server_s is None or now_s > self._last_server_s:
            return False  # authoritative heartbeat is mandatory
        self._sweep(now_s)
        previous = self._by_account.get(obs.account_key)
        if previous and obs.observed_s < previous.observed_s:
            return False  # drop reordered old locations
        if previous is None and len(self._by_account) >= MAX_PEERS:
            return False  # fail closed without unbounded memory
        self._by_account[obs.account_key] = obs
        return True

    def depart(self, account_key: str) -> None:
        self._by_account.pop(account_key, None)

    def snapshot(self, now_s: float) -> dict:
        """Public-only JSON projection. Unknown server != zero active hunters."""
        if not self._valid_time(now_s):
            raise ValueError("invalid snapshot clock")
        last = self._last_server_s
        if last is None or now_s < last or now_s-last > UNAVAILABLE_SERVER_S:
            return {"state": "unavailable", "online": None, "areas": [],
                    "location_precision": "area_only", "source": "authoritative_server"}
        if now_s-last > FRESH_SERVER_S:
            return {"state": "stale", "online": None, "areas": [],
                    "location_precision": "area_only", "source": "authoritative_server"}
        self._sweep(now_s)
        active = [o for o in self._by_account.values()
                  if o.observed_s <= now_s and now_s-o.observed_s <= MEMBER_TTL_S]
        # Reveal rough area counts only for explicit opt-in, non-PvP hunters.
        # Suppress tiny groups so a lone user cannot be tracked by region.
        by_area = Counter(o.area_key for o in active if o.share_area and not o.in_pvp)
        # Never publish a low-population area's KEY, not merely its count.
        # A suppressed location name alone can identify a lone consenting hunter.
        most = sorted(
            ((key, n) for key, n in by_area.items()
             if n >= MIN_PUBLIC_AREA_POPULATION),
            key=lambda x: (-x[1], x[0]),
        )[:MAX_AREAS]
        areas = [{"key": key, "hunters": n, "suppressed": False}
                 for key, n in most]
        return {"state": "live", "online": len(active), "areas": areas,
                "location_precision": "area_only", "source": "authoritative_server"}
