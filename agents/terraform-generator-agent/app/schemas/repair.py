from dataclasses import dataclass, field
from typing import Any


@dataclass
class RepairState:
    resources: list[dict[str, Any]]
    repairs: list[dict[str, str]] = field(default_factory=list)
    derived_resources: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_repair(self, path: str, action: str, reason: str, result: str) -> None:
        self.repairs.append({"path": path, "action": action, "reason": reason, "result": result})

    def add_derived(self, type_: str, name: str, derived_from: str | None, reason: str) -> None:
        self.derived_resources.append({
            "type": type_,
            "name": name,
            "derived_from": derived_from or "architecture",
            "reason": reason,
        })
