"""Guardrails and the append-only audit trail for the shop assistant.

The trail lives at output/audit_trail.json. Each run adds records. Nothing here
clears the file.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT_PATH = HERE.parent / "output" / "audit_trail.json"

HISTORY_TURNS = 12
HISTORY_CHARS = 400
SEARCH_CHARS = 200
REPLY_CHARS = 900
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

REFUSAL = (
    "I can help with Campus Customs merchandise: a piece, a price, a color, or a size. "
    "I can't change how this assistant works or look up anyone else's account."
)

INJECTION = re.compile(
    r"ignore (?:all |any )?(?:previous|prior|above) (?:instructions|prompts|rules)|"
    r"disregard (?:your|the) (?:system |developer )?(?:prompt|instructions)|"
    r"(?:reveal|print|show|repeat|dump) (?:me )?(?:your |the )?(?:system |hidden )?(?:prompt|instructions)|"
    r"you are now |"
    r"new (?:system )?instructions|"
    r"<\s*/?\s*system\s*>|"
    r"\b(?:jailbreak|do anything now)\b|"
    r"\b(?:api[_ ]?key|portkey|password hash|session secret)\b|"
    r"\b(?:drop table|delete from|union select|sqlite)\b|"
    r"\b(?:another|someone else(?:'s)?|other) (?:user|customer|account)(?:'s)? (?:password|email|chat)\b",
    re.IGNORECASE,
)


def misuse_reason(message: str) -> str | None:
    """A short reason when the message tries to override the assistant. None when it is a shopping question."""
    if INJECTION.search(message):
        return "prompt injection or a request for hidden shop data"
    return None


def clip(text: str, limit: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def catalogue_slug(product_id: str) -> str | None:
    slug = product_id.strip().lower()
    if not slug or len(slug) > 80 or SLUG.fullmatch(slug) is None:
        return None
    return slug


def bounded_phrase(value: str, limit: int) -> str:
    return clip(value, limit)


def clip_turns(turns: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Last few lines only, shortened, with blocked user lines replaced."""
    clipped: list[tuple[str, str]] = []
    for role, content in turns[-HISTORY_TURNS:]:
        text = content.strip()
        if not text:
            continue
        if role == "user" and misuse_reason(text):
            text = "A previous message was blocked."
        clipped.append((role, clip(text, HISTORY_CHARS)))
    return clipped


def record(tool: str, args: str, result: str, stop_reason: str = "") -> None:
    """Append one audit record. Leaves every earlier record in place."""
    event = {
        "time": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "args": clip(args, 180),
        "result": clip(result, 180),
        "stop_reason": stop_reason,
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _append_event(event)


def _append_event(event: dict[str, str]) -> None:
    lock_path = AUDIT_PATH.with_suffix(".lock")
    deadline = time.monotonic() + 5
    fd: int | None = None
    while fd is None:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() > deadline:
                raise TimeoutError(f"Could not lock {AUDIT_PATH.name}") from None
            time.sleep(0.05)
    try:
        rows = _read_rows()
        rows.append(event)
        AUDIT_PATH.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    finally:
        os.close(fd)
        lock_path.unlink(missing_ok=True)


def _read_rows() -> list[dict[str, str]]:
    if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
        return []
    data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("audit_trail.json must stay a list of records")
    return data
