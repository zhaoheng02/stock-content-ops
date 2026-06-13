import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class XAccount:
    handle: str
    category: str
    priority: int
    notes: str = ""


def load_accounts(path: str) -> List[XAccount]:
    csv_path = Path(path)
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    accounts: List[XAccount] = []
    seen = set()
    for index, row in enumerate(rows, start=2):
        account = _parse_row(row, index)
        normalized = account.handle.lower()
        if normalized in seen:
            raise ValueError(f"duplicate X account handle: {account.handle}")
        seen.add(normalized)
        accounts.append(account)

    return accounts


def _parse_row(row: dict, line_number: int) -> XAccount:
    handle = (row.get("handle") or "").strip().lstrip("@")
    category = (row.get("category") or "").strip()
    priority_text = (row.get("priority") or "3").strip()
    notes = (row.get("notes") or "").strip()

    if not handle:
        raise ValueError(f"missing handle at line {line_number}")
    if not category:
        raise ValueError(f"missing category at line {line_number}")

    try:
        priority = int(priority_text)
    except ValueError as error:
        raise ValueError(f"invalid priority at line {line_number}: {priority_text}") from error

    if priority < 1 or priority > 5:
        raise ValueError(f"priority must be 1-5 at line {line_number}")

    return XAccount(handle=handle, category=category, priority=priority, notes=notes)

