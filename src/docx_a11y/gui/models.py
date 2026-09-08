"""Data models for GUI batch Word document queue."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class BatchItem:
    path: Path
    status: str = "Pending"  # Pending, Auditing, Remediating, Completed, Failed
    paragraph_count: int = 0
    findings_count: int = 0
    critical_count: int = 0
    score: Optional[float] = None
    reports: Dict[str, Path] = field(default_factory=dict)
    remediated_path: Optional[Path] = None
    error_message: Optional[str] = None


class BatchQueue:
    def __init__(self):
        self.items: List[BatchItem] = []

    def add_file(self, path: Path | str) -> Optional[BatchItem]:
        p = Path(path).resolve()
        if not p.exists() or p.suffix.lower() != ".docx":
            return None
        if p.name.startswith("~$"):
            return None
        for item in self.items:
            if item.path == p:
                return None  # avoid duplicates
        item = BatchItem(path=p)
        self.items.append(item)
        return item

    def add_directory(self, dir_path: Path | str, recursive: bool = True) -> int:
        p = Path(dir_path).resolve()
        if not p.is_dir():
            return 0
        pattern = "**/*.docx" if recursive else "*.docx"
        added = 0
        for file_path in p.glob(pattern):
            if not file_path.name.startswith("~$"):
                if self.add_file(file_path):
                    added += 1
        return added

    def clear(self):
        self.items.clear()

    def __len__(self) -> int:
        return len(self.items)
