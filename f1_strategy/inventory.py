"""Tyre allocation feasibility checker.

In a real race weekend each team has a fixed set of tyre allocations.
Given the compound sequence a strategy requires, this module tells the
caller whether the inventory can fulfil it, and if so, whether any
used sets (pre-worn in practice or qualifying) are needed.

A "used" set is modelled as carrying USED_STARTING_AGE laps of
equivalent wear — it is feasible to run but at a hidden time cost not
captured in the base optimiser.
"""

from __future__ import annotations

from dataclasses import dataclass

USED_STARTING_AGE: int = 5  # laps of equivalent wear already on a used set


@dataclass
class TyreInventory:
    new: dict[str, int]   # compound → available new sets
    used: dict[str, int]  # compound → available used sets

    @classmethod
    def default(cls) -> TyreInventory:
        """Typical allocation for a standard race weekend."""
        return cls(new={"S": 2, "M": 3, "H": 4}, used={"S": 0, "M": 0, "H": 0})

    @classmethod
    def from_dict(cls, d: dict | None) -> TyreInventory:
        """Parse from the JSON payload; falls back to default if None or empty."""
        if not d:
            return cls.default()
        new: dict[str, int] = {}
        used: dict[str, int] = {}
        for k, v in d.items():
            new[k] = max(0, int(v.get("new", 0)))
            used[k] = max(0, int(v.get("used", 0)))
        return cls(new=new, used=used)

    def check(self, compounds: list[str]) -> dict:
        """Return feasibility info for a strategy's compound sequence.

        Allocates new sets first (preferred), then used sets. Returns:
          feasible       — True if inventory can cover all stints
          requires_used  — list of compound keys that fall back to used sets
          unavailable    — list of compound keys with no sets left at all
        """
        demand: dict[str, int] = {}
        for c in compounds:
            demand[c] = demand.get(c, 0) + 1

        rem_new = dict(self.new)
        rem_used = dict(self.used)
        requires_used: list[str] = []
        unavailable: list[str] = []

        for c, count in demand.items():
            avail_new = rem_new.get(c, 0)
            avail_used = rem_used.get(c, 0)
            if avail_new + avail_used < count:
                unavailable.append(c)
            else:
                from_new = min(count, avail_new)
                from_used = count - from_new
                rem_new[c] -= from_new
                rem_used[c] -= from_used
                if from_used > 0:
                    requires_used.append(c)

        return {
            "feasible": len(unavailable) == 0,
            "requires_used": requires_used,
            "unavailable": unavailable,
        }

    def to_dict(self) -> dict:
        return {"new": self.new, "used": self.used}