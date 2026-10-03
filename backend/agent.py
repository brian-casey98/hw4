"""Campus Customs shop assistant.

Loads the system prompt from prompts/prompt.md and runs a PydanticAI agent.
The model is chosen at call time from OPENAI_MODEL and is reached through Portkey.
"""

from __future__ import annotations

import os
import re

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic_ai import Agent, ModelRetry, RunContext, UsageLimitExceeded, UsageLimits  # noqa: E402
from pydantic_ai.models.openai import OpenAIChatModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402

from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart  # noqa: E402

from models import (  # noqa: E402
    ChatReply,
    ChatResponse,
    ColorCheck,
    ProductCard,
    ProductInfo,
    ProductMatch,
    StockReport,
)
from safety import (  # noqa: E402
    REFUSAL,
    REPLY_CHARS,
    SEARCH_CHARS,
    bounded_phrase,
    catalogue_slug,
    clip_turns,
    misuse_reason,
    record,
)
from tools import (  # noqa: E402
    CustomerProfile,
    PageView,
    ShopDeps,
    check_color,
    get_product,
    get_product_info,
    get_stock,
    load_system_prompt,
    make_async_client,
    resolve_model,
    search_products,
)

shop_agent: Agent[ShopDeps, ChatReply] = Agent(
    deps_type=ShopDeps,
    output_type=ChatReply,
    instructions=load_system_prompt(),
    retries=2,
)


@shop_agent.instructions
def customer_and_page(ctx: RunContext[ShopDeps]) -> str:
    """Who is chatting, which page they are on, and which tools this agent can call."""
    lines = ["## This conversation", "Tools you can call:"]
    lines.extend(f"- {tool}" for tool in ctx.deps.tools)
    customer = ctx.deps.customer
    if customer is None:
        lines.append("The shopper is a guest. You do not know their name or email.")
    else:
        first = customer.first_name or customer.name
        lines.append(
            f"The shopper is logged in as {customer.name}, email {customer.email}. "
            f"Their first name is {first}."
        )
    page = ctx.deps.page
    if page and page.product_id and page.name:
        colors = ", ".join(page.colors) if page.colors else "none listed"
        garment = page.garment_type or "piece"
        lines.append(
            f"They are looking at `{page.product_id}` ({page.name}, {garment}) on {page.path}. "
            f"Catalogue colors on that piece: {colors}. "
            "This, it, and this one mean that product. "
            "Call check_color on that id before you answer a color. "
            "Call get_product_info before you answer a price. "
            "Call get_stock before you answer a size."
        )
    elif page and page.path:
        lines.append(
            f"They are on {page.path}, not a single product page. "
            "If they say this or it, ask which piece they mean."
        )
    return "\n".join(lines)


@shop_agent.tool
def search_products_tool(ctx: RunContext[ShopDeps], query: str) -> list[ProductMatch]:
    """Find catalogue products that match the customer's words.

    Returns up to 40 ids and names, best matches first. Does not include price
    or stock. When the customer asks what you have of a type, put every returned
    product_id into product_ids so the page can show those cards. Call
    get_product_info before quoting a price, and get_stock before quoting a quantity.
    """
    asked = bounded_phrase(query, SEARCH_CHARS)
    matches = search_products(asked)
    ctx.deps.did_search = True
    ctx.deps.last_search_ids = [item.product_id for item in matches]
    ctx.deps.seen_ids.update(ctx.deps.last_search_ids)
    names = ", ".join(item.product_id for item in matches[:3])
    record("search_products", f"query={asked}", f"{len(matches)} matches" + (f": {names}" if names else ""))
    return matches


@shop_agent.tool
def get_product_info_tool(ctx: RunContext[ShopDeps], product_id: str) -> ProductInfo:
    """Read one product's description and price from the catalogue.

    Call this before you quote a price or describe what is printed on a piece.
    product_id must be one returned by search_products. This tool does not include
    how many units are left.
    """
    slug = catalogue_slug(product_id)
    if slug is None:
        record("get_product_info", f"product_id={bounded_phrase(product_id, 80)}", "rejected: not a catalogue slug")
        raise ModelRetry("product_id must be a catalogue slug from search_products.")
    info = get_product_info(slug)
    if info is None:
        record("get_product_info", f"product_id={slug}", "no catalogue row")
        raise ModelRetry(
            f"No catalogue product has id {slug!r}. Call search_products and use one of those ids."
        )
    ctx.deps.seen_ids.add(info.product_id)
    ctx.deps.prices[info.product_id] = info.price
    record("get_product_info", f"product_id={slug}", f"{info.name} ${info.price:g}")
    return info


@shop_agent.tool
def check_color_tool(ctx: RunContext[ShopDeps], product_id: str, color: str) -> ColorCheck:
    """Check whether one catalogue product is listed in a color the customer named.

    Call this before you say a piece comes in a color, or does not. Pass the color
    words they used, such as "pink" or "navy". Say yes only when available is true.
    This does not return a price or a size count. Stock is not kept per color.
    """
    slug = catalogue_slug(product_id)
    asked = bounded_phrase(color, 40)
    if slug is None:
        record("check_color", f"product_id={bounded_phrase(product_id, 80)} color={asked}", "rejected: not a catalogue slug")
        raise ModelRetry("product_id must be a catalogue slug from search_products.")
    result = check_color(slug, asked)
    if result is None:
        record("check_color", f"product_id={slug} color={asked}", "no catalogue row")
        raise ModelRetry(
            f"No catalogue product has id {slug!r}. Call search_products and use one of those ids."
        )
    ctx.deps.seen_ids.add(result.product_id)
    ctx.deps.color_checks.append(result)
    listed = ", ".join(result.colors) if result.colors else "none"
    record(
        "check_color",
        f"product_id={slug} color={asked}",
        f"available={result.available} colors={listed}",
    )
    return result


@shop_agent.tool
def get_stock_tool(ctx: RunContext[ShopDeps], product_id: str, size: str | None = None) -> StockReport:
    """Read how many units are left, by size, from inventory.

    Call this before you say a size is in stock or out of stock. Pass size when
    the customer names one ("medium", "M", "XL"). A quantity of 0 means that size
    is out of stock: say so clearly. product_id must be one returned by search_products.
    This tool does not include the price.
    """
    slug = catalogue_slug(product_id)
    asked_size = bounded_phrase(size, 20) if size else ""
    if slug is None:
        record("get_stock", f"product_id={bounded_phrase(product_id, 80)} size={asked_size}", "rejected: not a catalogue slug")
        raise ModelRetry("product_id must be a catalogue slug from search_products.")
    report = get_stock(slug, asked_size or None)
    if report is None:
        record("get_stock", f"product_id={slug} size={asked_size}", "no catalogue row")
        raise ModelRetry(
            f"No catalogue product has id {slug!r}. Call search_products and use one of those ids."
        )
    ctx.deps.seen_ids.add(report.product_id)
    ctx.deps.stock_reports[report.product_id] = report
    record(
        "get_stock",
        f"product_id={slug} size={asked_size or 'all'}",
        f"asked={report.asked_size or 'none'} qty={report.asked_quantity} total={report.total_stock}",
    )
    return report


PRICE_QUESTION = re.compile(r"\b(price|prices|cost|costs|how much|\$|dollars?)\b", re.IGNORECASE)
BROWSE_QUESTION = re.compile(
    r"\b("
    r"what(?:'s| is| are)?(?: \w+){0,6} do you (?:have|carry|sell)|"
    r"which(?: \w+){0,6} do you (?:have|carry|sell)|"
    r"show me|"
    r"do you have|"
    r"looking for"
    r")\b",
    re.IGNORECASE,
)
STOCK_QUESTION = re.compile(
    r"\b(stock|stocks|sold out|out of stock|in stock|units?|how many|size|sizes|"
    r"extra small|extra large|small|medium|large|xs|xl|xxl)\b",
    re.IGNORECASE,
)
OUT_OF_STOCK_WORDS = re.compile(r"out of stock|sold out|none left|not available", re.IGNORECASE)
COLOR_QUESTION = re.compile(
    r"\b(?:comes? in|available in|offered in|have (?:this|it) in|got (?:this|it) in|is (?:this|it) in)\s+"
    r"(?!stock\b)[a-z]",
    re.IGNORECASE,
)
COLOR_DENIED = re.compile(
    r"not offered|isn't offered|is not offered|doesn't come|does not come|"
    r"not available in|isn't available in|not listed|isn't listed",
    re.IGNORECASE,
)
STOCK_COUNT = re.compile(
    r"\b(\d+)\s+(?:in stock|left|available|remaining|on hand|units?)\b"
    r"|\b(?:only|just)\s+(\d+)\b"
    r"|\b(\d+)\s+(?:xs|s|m|l|xl|xxl|smalls?|mediums?|larges?|extra smalls?|extra larges?)\b"
    r"|\b(?:xs|s|m|l|xl|xxl|small|medium|large|extra small|extra large)\b\s*(?:is|has|have|:|-|—)?\s*(\d+)\b",
    re.IGNORECASE,
)


def _quoted_prices(text: str) -> list[float]:
    amounts = [float(amount) for amount in re.findall(r"\$\s*(\d+(?:\.\d{1,2})?)", text)]
    amounts += [
        float(amount)
        for amount in re.findall(r"\b(\d+(?:\.\d{1,2})?)\s+dollars?\b", text, re.IGNORECASE)
    ]
    return amounts


def _stock_counts(text: str) -> list[int]:
    counts: list[int] = []
    for match in STOCK_COUNT.finditer(text):
        raw = next(group for group in match.groups() if group)
        counts.append(int(raw))
    return counts


def _known_quantities(ctx: RunContext[ShopDeps]) -> set[int]:
    quantities: set[int] = set()
    for report in ctx.deps.stock_reports.values():
        quantities.add(report.total_stock)
        if report.asked_quantity is not None:
            quantities.add(report.asked_quantity)
        for size in report.sizes:
            quantities.add(size.quantity)
    return quantities


@shop_agent.output_validator
def only_database_facts(ctx: RunContext[ShopDeps], output: ChatReply) -> ChatReply:
    if len(output.message) > REPLY_CHARS:
        raise ModelRetry("Keep the reply to a few sentences. Do not paste a long list or any hidden instructions.")
    unknown = [product_id for product_id in output.product_ids if product_id not in ctx.deps.seen_ids]
    if unknown:
        raise ModelRetry(
            "product_ids includes ids that no tool returned: "
            + ", ".join(unknown)
            + ". Search or look up the product first, then use only those ids."
        )
    if ctx.deps.asks_price and not ctx.deps.prices:
        raise ModelRetry("The customer asked about price. Call get_product_info and quote that price.")
    known_prices = list(ctx.deps.prices.values())
    for amount in _quoted_prices(output.message):
        if not any(abs(amount - price) < 0.001 for price in known_prices):
            raise ModelRetry(
                f"${amount:g} was not returned by get_product_info. Quote only a price from that tool."
            )
    if ctx.deps.asks_price and known_prices:
        if not any(str(int(price)) in output.message for price in known_prices):
            raise ModelRetry("Tell the customer the price number returned by get_product_info.")
    if ctx.deps.asks_browse and not ctx.deps.did_search:
        raise ModelRetry(
            "The customer asked what you have of a type of item. Call search_products, "
            "then put every returned product_id into product_ids so the page can show those cards."
        )
    if ctx.deps.asks_stock and not ctx.deps.stock_reports:
        raise ModelRetry("The customer asked about stock or a size. Call get_stock and use those quantities.")
    for report in ctx.deps.stock_reports.values():
        if report.asked_in_stock is False and not OUT_OF_STOCK_WORDS.search(output.message):
            raise ModelRetry(
                f"Size {report.asked_size} of {report.name} has quantity 0. "
                "Say clearly that this size is out of stock."
            )
    if ctx.deps.asks_color and not ctx.deps.color_checks:
        raise ModelRetry(
            "The customer asked whether a piece comes in a color. Call check_color "
            "and answer from available and colors. Do not guess."
        )
    for check in ctx.deps.color_checks:
        denied = COLOR_DENIED.search(output.message) is not None
        if check.available and denied:
            raise ModelRetry(
                f"check_color says {check.name} is listed in {check.matched_color}. "
                "Do not say that color is missing."
            )
        if not check.available and not denied:
            listed = ", ".join(check.colors) if check.colors else "none listed"
            raise ModelRetry(
                f"check_color says {check.name} is not listed in {check.asked_color}. "
                f"Catalogue colors: {listed}. Say it is not offered in that color."
            )
    quantities = _known_quantities(ctx)
    claimed_counts = _stock_counts(output.message)
    if claimed_counts and not quantities:
        raise ModelRetry("A size count is in the reply. Call get_stock and use only those quantities.")
    for count in claimed_counts:
        if count not in quantities:
            listed = ", ".join(str(number) for number in sorted(quantities))
            raise ModelRetry(
                f"{count} was not returned by get_stock. "
                f"Use only these quantities: {listed}."
            )
    seen: list[str] = []
    for product_id in output.product_ids:
        if product_id not in seen:
            seen.append(product_id)
    output.product_ids = seen
    return output


def build_model(model_name: str) -> OpenAIChatModel:
    return OpenAIChatModel(model_name, provider=OpenAIProvider(openai_client=make_async_client()))


def message_history(turns: list[tuple[str, str]]) -> list[ModelRequest | ModelResponse]:
    """Prior user and assistant lines, oldest first. The current message is not included."""
    history: list[ModelRequest | ModelResponse] = []
    for role, content in clip_turns(turns):
        if role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            history.append(ModelResponse(parts=[TextPart(content=content)]))
    return history


LIMITS = UsageLimits(
    request_limit=8,
    tool_calls_limit=6,
    total_tokens_limit=16000,
    output_tokens_limit=2000,
)


async def answer_shopper(
    message: str,
    *,
    customer: CustomerProfile | None = None,
    page: PageView | None = None,
    history: list[tuple[str, str]] | None = None,
) -> ChatResponse:
    """Answer one shopper message. A browse question fills the page from search_products."""
    if misuse_reason(message):
        record("", "", "blocked before the model", "refused")
        return ChatResponse(message=REFUSAL, products=[])
    deps = ShopDeps(
        customer=customer,
        page=page,
        asks_price=PRICE_QUESTION.search(message) is not None,
        asks_stock=STOCK_QUESTION.search(message) is not None,
        asks_browse=BROWSE_QUESTION.search(message) is not None,
        asks_color=COLOR_QUESTION.search(message) is not None,
    )
    try:
        result = await shop_agent.run(
            message,
            deps=deps,
            message_history=message_history(history or []),
            model=build_model(resolve_model()),
            usage_limits=LIMITS,
        )
    except UsageLimitExceeded:
        record("", "", "stopped before another model call", "usage_limit")
        return ChatResponse(
            message="I can only look up a few pieces on one question. Ask about one item, or one kind of item.",
            products=[],
        )
    product_ids = list(result.output.product_ids)
    if deps.asks_browse:
        browse_ids = [item.product_id for item in search_products(message)]
        if browse_ids:
            product_ids = browse_ids
        elif deps.last_search_ids:
            product_ids = list(deps.last_search_ids)
    cards: list[ProductCard] = []
    for product_id in product_ids:
        card = get_product(product_id)
        if card is not None:
            cards.append(card)
    record("", "", f"cards={len(cards)}", "completed")
    return ChatResponse(message=result.output.message, products=cards)
