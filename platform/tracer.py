from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path


class Trace:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or Path("traces")
        self.events: list[tuple[str, str]] = []

    def record(self, step: str, detail: object) -> None:
        self.events.append((step, str(detail)))

    def write(self) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"run_{datetime.now():%Y%m%d_%H%M%S}.html"
        rows = "".join(f"<tr><td>{escape(step)}</td><td><pre>{escape(detail)}</pre></td></tr>" for step, detail in self.events)
        path.write_text(f"<html><body><h1>Payment exception trace</h1><table>{rows}</table></body></html>", encoding="utf-8")
        return path
