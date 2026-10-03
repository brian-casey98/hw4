from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class SizeStock(BaseModel):
    size: str
    quantity: int


class ProductCard(BaseModel):
    """One catalogue piece the chat panel can render. Filled from the database, not from the model."""

    product_id: str
    name: str
    garment_type: str
    description: str
    price: float
    colors: list[str]
    image_url: str
    inventory: list[SizeStock]
    total_stock: int


class ProductMatch(BaseModel):
    """A search hit. Identity only, so a price or a quantity has to come from a later tool."""

    product_id: str = Field(description="Catalogue slug. Pass this to get_product_info and get_stock.")
    name: str = Field(description="Product title from the catalogue.")
    garment_type: str = Field(description="Kind of garment, used to tell similar names apart.")


class ProductInfo(BaseModel):
    """Description and price for one product, read from the catalogue row."""

    product_id: str
    name: str
    garment_type: str
    description: str = Field(description="Catalogue description. Use this when the customer asks what the piece is.")
    price: float = Field(description="Dollar price from catalogue.price. This is the only price to quote.")
    colors: list[str] = Field(
        description="Color names printed or used on the piece. A color does not have its own stock count."
    )
    stock_note: str = Field(
        description="Reminder that units on hand are not in this result. Call get_stock for them."
    )


class ColorCheck(BaseModel):
    """Whether one catalogue color list includes the color the customer asked about."""

    product_id: str
    name: str
    asked_color: str = Field(description="The color words the customer used.")
    available: bool = Field(description="True only when that color is on the catalogue row.")
    matched_color: str | None = Field(description="The catalogue color that matched, if any.")
    colors: list[str] = Field(description="Every color name stored for this piece.")
    note: str = Field(description="Stock is not per color. This result is only the color list.")


class SizeCount(BaseModel):
    """One inventory row: how many of this size are left for the whole piece."""

    size: str = Field(description="Shop size: XS, S, M, L, XL, or XXL.")
    quantity: int = Field(description="Units on hand. Zero means that size is out of stock.")
    in_stock: bool = Field(description="True only when quantity is greater than zero.")


class StockReport(BaseModel):
    """Size counts for one product, read from inventory."""

    product_id: str
    name: str
    sizes: list[SizeCount]
    total_stock: int = Field(description="Sum of quantity across every size.")
    out_of_stock_sizes: list[str] = Field(
        description="Sizes whose quantity is 0. Tell the customer each of these is out of stock when they ask about sizes."
    )
    asked_size: str | None = Field(description="The shop size the customer asked about, if they named one.")
    asked_quantity: int | None = Field(description="Units left in asked_size. Zero means out of stock.")
    asked_in_stock: bool | None = Field(
        description="False means the asked size is out of stock. Say that clearly. Null if they did not name a size."
    )
    size_note: str | None = Field(description="Set when the named size is not one the shop carries.")
    price_note: str = Field(description="Reminder that the dollar price is not in this result. Call get_product_info for it.")


class ChatReply(BaseModel):
    """Structured answer the agent itself produces."""

    message: str = Field(description="What to say in the chat panel.")
    product_ids: list[str] = Field(
        default_factory=list,
        description="Catalogue ids to show as cards. Only ids a tool returned.",
    )


class PageHint(BaseModel):
    """Where the shopper is on the site. The server checks product_id against the catalogue."""

    path: str = Field(default="", max_length=300)
    product_id: str | None = Field(default=None, max_length=120)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    page: PageHint | None = None


class ChatResponse(BaseModel):
    """What the website receives. Product cards are loaded from the database."""

    message: str
    products: list[ProductCard]
