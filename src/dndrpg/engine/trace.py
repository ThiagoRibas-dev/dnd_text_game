from __future__ import annotations
from typing import List

class TraceSession:
    def __init__(self) -> None:
        self.lines: List[str] = []

    def add(self, line: str) -> None:
        self.lines.append(line)

    def extend(self, many: list[str]) -> None:
        self.lines.extend(many)

    def dump(self) -> list[str]:
        return list(self.lines)
