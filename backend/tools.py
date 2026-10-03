"""Catalogue lookups and model wiring for the shop assistant.

The agent may only learn prices and stock through these functions. They read
campus_customs.db directly.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values
from openai import AsyncOpenAI

from models import ColorCheck, ProductCard, ProductInfo, ProductMatch, SizeCount, SizeStock, StockReport

HERE = Path(__file__).resolve().parent
HW_ROOT = HERE.parent
COURSE_ROOT = HW_ROOT.parent
PROMPT_PATH = HERE / "prompts" / "prompt.md"

ALLOWED_MODELS = (
    "gpt-5.6-luna",
    "gpt-5.6-terra",
    "gpt-5.6-sol",
    "gpt-5.6-astra",
)

SIZE_ORDER = ("XS", "S", "M", "L", "XL", "XXL")
SIZE_ALIASES = {
    "xs": "XS",
    "xsmall": "XS",
    "extrasmall": "XS",
    "s": "S",
    "small": "S",
    "m": "M",
    "med": "M",
    "medium": "M",
    "l": "L",
    "large": "L",
    "xl": "XL",
    "xlarge": "XL",
    "extralarge": "XL",
    "xxl": "XXL",
    "2xl": "XXL",
    "xxlarge": "XXL",
}
STOCK_NOTE = "Units in stock are not included here. Call get_stock for size counts."
PRICE_NOTE = "Price is not included here. Call get_product_info for the dollar price."

STOP_WORDS = {
    "a",
    "an",
    "and",
    "any",
    "are",
    "do",
    "for",
    "have",
    "how",
    "in",
    "is",
    "it",
    "me",
    "much",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "what",
    "with",
    "you",
}


class ConfigError(RuntimeError):
    """The chat model or Portkey key is not configured."""


@dataclass
class CustomerProfile:
    """The signed-in shopper. Guests leave this empty."""

    name: str
    first_name: str
    email: str


@dataclass
class PageView:
    """What the shopper is looking at. Filled from the catalogue when they are on a product page."""

    path: str
    product_id: str | None = None
    name: str | None = None
    garment_type: str | None = None
    colors: list[str] = field(default_factory=list)


TOOL_GUIDE = (
    "search_products: find catalogue pieces from the customer's words. No price or stock.",
    "get_product_info: one product's description and price.",
    "check_color: whether a named color is on that product. Say yes only when available is true.",
    "get_stock: units left in each size. A quantity of 0 is out of stock.",
)


@dataclass
class ShopDeps:
    customer: CustomerProfile | None = None
    page: PageView | None = None
    tools: tuple[str, ...] = TOOL_GUIDE
    seen_ids: set[str] = field(default_factory=set)
    prices: dict[str, float] = field(default_factory=dict)
    stock_reports: dict[str, StockReport] = field(default_factory=dict)
    color_checks: list[ColorCheck] = field(default_factory=list)
    asks_color: bool = False
    asks_price: bool = False
    asks_stock: bool = False
    asks_browse: bool = False
    did_search: bool = False
    last_search_ids: list[str] = field(default_factory=list)


def load_environment() -> None:
    """Fill empty env vars from backend/.env, then HW4/.env, then the course .env."""
    for path in (HERE / ".env", HW_ROOT / ".env", COURSE_ROOT / ".env"):
        if not path.is_file():
            continue
        for key, value in dotenv_values(path).items():
            if value and not os.environ.get(key):
                os.environ[key] = value


def load_system_prompt() -> str:
    if not PROMPT_PATH.is_file():
        raise ConfigError(f"Missing system prompt: {PROMPT_PATH}")
    text = PROMPT_PATH.read_text(encoding="utf-8").strip()
    if not text:
        raise ConfigError(f"System prompt is empty: {PROMPT_PATH}")
    return text


def resolve_model() -> str:
    load_environment()
    model = (os.getenv("OPENAI_MODEL") or "").strip()
    allowed = ", ".join(ALLOWED_MODELS)
    if not model:
        raise ConfigError(
            "No model selected. Set OPENAI_MODEL in the course .env to one of: " + allowed
        )
    if model not in ALLOWED_MODELS:
        raise ConfigError(f"Unsupported model {model!r}. Allowed models: {allowed}")
    return model


def portkey_key() -> str:
    load_environment()
    key = (os.getenv("PORTKEY_API_KEY") or "").strip()
    if not key:
        raise ConfigError("PORTKEY_API_KEY is not set. Add it to the course .env.")
    return key


def make_async_client() -> AsyncOpenAI:
    key = portkey_key()
    return AsyncOpenAI(
        api_key=key,
        base_url="https://api.portkey.ai/v1",
        default_headers={"x-portkey-api-key": key},
    )


def database_path() -> Path:
    for path in (
        HW_ROOT / "data" / "data" / "campus_customs.db",
        HW_ROOT / "data" / "campus_customs.db",
    ):
        if path.exists():
            return path
    raise ConfigError("campus_customs.db was not found under data/.")


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(database_path())
    connection.row_factory = sqlite3.Row
    return connection


def _json_list(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _card_from_row(connection: sqlite3.Connection, row: sqlite3.Row) -> ProductCard:
    sizes = connection.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY id",
        (row["product_id"],),
    ).fetchall()
    inventory = [SizeStock(size=item["size"], quantity=item["quantity"]) for item in sizes]
    return ProductCard(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        price=row["price"],
        colors=_json_list(row["colors"]),
        image_url=f"/media/{row['image_file_path']}",
        inventory=inventory,
        total_stock=sum(item.quantity for item in inventory),
    )


def normalize_size(size: str | None) -> tuple[str | None, str | None]:
    """Map a customer's size word to XS–XXL. The note is set when the word is not a shop size."""
    if size is None or not str(size).strip():
        return None, None
    key = re.sub(r"[^a-z0-9]", "", size.lower())
    canonical = SIZE_ALIASES.get(key)
    if canonical is None:
        return None, (
            f"No size named {size.strip()}. The shop sizes are XS, S, M, L, XL, and XXL."
        )
    return canonical, None


def _size_counts(connection: sqlite3.Connection, product_id: str) -> list[SizeCount]:
    rows = connection.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ?",
        (product_id,),
    ).fetchall()
    by_size = {row["size"]: int(row["quantity"]) for row in rows}
    counts: list[SizeCount] = []
    for size in SIZE_ORDER:
        if size not in by_size:
            continue
        quantity = by_size[size]
        counts.append(SizeCount(size=size, quantity=quantity, in_stock=quantity > 0))
    for size, quantity in by_size.items():
        if size in SIZE_ORDER:
            continue
        counts.append(SizeCount(size=size, quantity=quantity, in_stock=quantity > 0))
    return counts


def _search_tokens(query: str) -> list[str]:
    raw = [
        token
        for token in re.findall(r"[a-z0-9]+", query.lower())
        if len(token) > 1 and token not in STOP_WORDS
    ]
    tokens: list[str] = []
    for token in raw:
        tokens.append(token)
        if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
            stem = token[:-1]
            if stem not in STOP_WORDS:
                tokens.append(stem)
        if token in {"tee", "tees", "tshirt", "tshirts"}:
            tokens.extend(["shirt", "t-shirt"])
    seen: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.append(token)
    return seen


def search_products(query: str, limit: int = 40) -> list[ProductMatch]:
    tokens = _search_tokens(query)
    connection = connect()
    try:
        rows = connection.execute("SELECT * FROM catalogue").fetchall()
        scored: list[tuple[int, sqlite3.Row]] = []
        for row in rows:
            name = row["name"].lower()
            garment = row["garment_type"].lower()
            tags = row["search_tags"].lower()
            details = " ".join([row["description"], row["colors"]]).lower()
            score = 0
            for token in tokens:
                if token in name or token in garment:
                    score += 3
                elif token in tags:
                    score += 2
                elif token in details:
                    score += 1
            if score:
                scored.append((score, row))
        strong = [item for item in scored if item[0] >= 3]
        chosen = strong or scored
        chosen.sort(key=lambda item: (-item[0], item[1]["name"].lower()))
        return [
            ProductMatch(
                product_id=row["product_id"],
                name=row["name"],
                garment_type=row["garment_type"],
            )
            for _score, row in chosen[:limit]
        ]
    finally:
        connection.close()


def _catalogue_row(connection: sqlite3.Connection, product_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM catalogue WHERE product_id = ?",
        (product_id,),
    ).fetchone()


def get_product_info(product_id: str) -> ProductInfo | None:
    connection = connect()
    try:
        row = _catalogue_row(connection, product_id)
        if row is None:
            return None
        return ProductInfo(
            product_id=row["product_id"],
            name=row["name"],
            garment_type=row["garment_type"],
            description=row["description"],
            price=row["price"],
            colors=_json_list(row["colors"]),
            stock_note=STOCK_NOTE,
        )
    finally:
        connection.close()


def check_color(product_id: str, color: str) -> ColorCheck | None:
    """True only when the asked color is on this catalogue row. Stock is not per color."""
    connection = connect()
    try:
        row = _catalogue_row(connection, product_id)
        if row is None:
            return None
        colors = _json_list(row["colors"])
        asked = " ".join(color.lower().split())
        matched = _match_color(asked, colors)
        if matched is None:
            note = (
                f"{row['name']} is not listed in {color.strip() or 'that color'}. "
                "Catalogue colors: "
                + (", ".join(colors) if colors else "none listed")
                + ". Stock is not kept per color."
            )
        else:
            note = (
                f"{row['name']} is listed in {matched}. "
                "Stock is not kept per color; size counts are for the whole piece."
            )
        return ColorCheck(
            product_id=row["product_id"],
            name=row["name"],
            asked_color=color.strip(),
            available=matched is not None,
            matched_color=matched,
            colors=colors,
            note=note,
        )
    finally:
        connection.close()


def _match_color(asked: str, colors: list[str]) -> str | None:
    if not asked or asked in {"stock", "size", "sizes", "the", "a", "it", "this", "one"}:
        return None
    for color in colors:
        hay = color.lower()
        if asked == hay or asked in hay:
            return color
    return None


def get_stock(product_id: str, size: str | None = None) -> StockReport | None:
    connection = connect()
    try:
        row = _catalogue_row(connection, product_id)
        if row is None:
            return None
        sizes = _size_counts(connection, product_id)
        asked, size_note = normalize_size(size)
        asked_quantity: int | None = None
        asked_in_stock: bool | None = None
        if asked is not None:
            match = next((item for item in sizes if item.size == asked), None)
            if match is None:
                size_note = f"No {asked} row is stored for this product."
            else:
                asked_quantity = match.quantity
                asked_in_stock = match.in_stock
        return StockReport(
            product_id=row["product_id"],
            name=row["name"],
            sizes=sizes,
            total_stock=sum(item.quantity for item in sizes),
            out_of_stock_sizes=[item.size for item in sizes if not item.in_stock],
            asked_size=asked,
            asked_quantity=asked_quantity,
            asked_in_stock=asked_in_stock,
            size_note=size_note,
            price_note=PRICE_NOTE,
        )
    finally:
        connection.close()


def page_view(path: str, product_id: str | None) -> PageView:
    """Build the page the shopper is on. A product id is filled only when it is in the catalogue."""
    view = PageView(path=(path or "/").strip() or "/")
    if not product_id or not product_id.strip():
        return view
    info = get_product_info(product_id.strip())
    if info is None:
        return view
    view.product_id = info.product_id
    view.name = info.name
    view.garment_type = info.garment_type
    view.colors = list(info.colors)
    return view


def recent_turns(user_id: int, limit: int = 12) -> list[tuple[str, str]]:
    """The latest saved lines for this account, oldest first. The new message is not in here yet."""
    connection = connect()
    try:
        rows = connection.execute(
            """
            SELECT role, content FROM chat_messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    finally:
        connection.close()
    return [(row["role"], row["content"]) for row in reversed(rows)]


def _saved_products(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    products: list[dict] = []
    for item in parsed:
        if not isinstance(item, dict) or not item.get("product_id"):
            continue
        products.append(
            {
                "product_id": item.get("product_id"),
                "name": item.get("name") or "",
                "garment_type": item.get("garment_type") or "",
                "description": item.get("description") or "",
                "price": item.get("price") or 0,
                "image_url": item.get("image_url") or "",
                "colors": item.get("colors") if isinstance(item.get("colors"), list) else [],
            }
        )
    return products


def list_chat(user_id: int) -> list[dict]:
    connection = connect()
    try:
        rows = connection.execute(
            """
            SELECT id, role, content, products_json, created_at
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY id
            """,
            (user_id,),
        ).fetchall()
    finally:
        connection.close()
    return [
        {
            "id": row["id"],
            "role": row["role"],
            "content": row["content"],
            "products": _saved_products(row["products_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def save_turn(user_id: int, user_text: str, assistant_text: str, products: list[ProductCard]) -> None:
    payload = json.dumps([item.model_dump() for item in products])
    connection = connect()
    try:
        connection.execute(
            "INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)",
            (user_id, user_text),
        )
        connection.execute(
            """
            INSERT INTO chat_messages (user_id, role, content, products_json)
            VALUES (?, 'assistant', ?, ?)
            """,
            (user_id, assistant_text, payload),
        )
        connection.commit()
    finally:
        connection.close()


def get_product(product_id: str) -> ProductCard | None:
    connection = connect()
    try:
        row = connection.execute(
            "SELECT * FROM catalogue WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        if row is None:
            return None
        return _card_from_row(connection, row)
    finally:
        connection.close()
