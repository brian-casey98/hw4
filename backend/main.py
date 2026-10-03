"""Campus Customs API.

Serves the catalogue, accounts, and the shop assistant. Run from this directory:

    uvicorn main:app --reload --port 8000
"""

import json
import re
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from auth import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    hash_password,
    make_session_token,
    read_session_token,
    verify_password,
)
from models import ChatRequest, ChatResponse, LoginRequest, RegisterRequest
from tools import CustomerProfile, list_chat, page_view, recent_turns, save_turn

ROOT = Path(__file__).resolve().parents[1]
DB_CANDIDATES = (
    ROOT / "data" / "data" / "campus_customs.db",
    ROOT / "data" / "campus_customs.db",
)
PRODUCTS_CANDIDATES = (
    ROOT / "data" / "data" / "products",
    ROOT / "data" / "products",
)
SIZE_ORDER = ("XS", "S", "M", "L", "XL", "XXL")

app = FastAPI(title="Campus Customs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DUMMY_PASSWORD_HASH = hash_password("not-a-real-password")


def database_path() -> Path:
    for path in DB_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("campus_customs.db was not found under data/.")


def products_dir() -> Path:
    for path in PRODUCTS_CANDIDATES:
        if path.is_dir():
            return path
    raise FileNotFoundError("The products image folder was not found under data/.")


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(database_path())
    connection.row_factory = sqlite3.Row
    return connection


def json_list(value: str) -> list[str]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def product_payload(row: sqlite3.Row) -> dict:
    image_file_path = row["image_file_path"]
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "colors": json_list(row["colors"]),
        "search_tags": json_list(row["search_tags"]),
        "image_file_path": image_file_path,
        "image_url": f"/media/{image_file_path}",
        "price": row["price"],
    }


def size_rank(size: str) -> tuple[int, str]:
    try:
        return (SIZE_ORDER.index(size), size)
    except ValueError:
        return (len(SIZE_ORDER), size)


@app.get("/api/products")
def list_products() -> list[dict]:
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT * FROM catalogue ORDER BY name COLLATE NOCASE"
        ).fetchall()
    finally:
        connection.close()
    return [product_payload(row) for row in rows]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    connection = connect()
    try:
        row = connection.execute(
            "SELECT * FROM catalogue WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        sizes = connection.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?",
            (product_id,),
        ).fetchall()
    finally:
        connection.close()

    payload = product_payload(row)
    payload["inventory"] = [
        {"size": size["size"], "quantity": size["quantity"]}
        for size in sorted(sizes, key=lambda item: size_rank(item["size"]))
    ]
    return payload


def public_user(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "first_name": row["first_name"] or "",
        "last_name": row["last_name"] or "",
        "email": row["email"],
    }


def clean_name(value: str, label: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise HTTPException(status_code=400, detail=f"Enter a {label}.")
    return cleaned


def clean_email(value: str) -> str:
    email = value.strip().lower()
    if EMAIL_PATTERN.fullmatch(email) is None:
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    return email


def user_by_id(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def user_from_request(request: Request) -> sqlite3.Row | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    user_id = read_session_token(token)
    if user_id is None:
        return None
    connection = connect()
    try:
        return user_by_id(connection, user_id)
    finally:
        connection.close()


def start_session(response: Response, user_id: int) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=make_session_token(user_id),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


@app.post("/api/auth/register")
def register(body: RegisterRequest, response: Response) -> dict:
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    first_name = clean_name(body.first_name, "first name")
    last_name = clean_name(body.last_name, "last name")
    email = clean_email(body.email)
    connection = connect()
    try:
        taken = connection.execute(
            "SELECT id FROM users WHERE email = ? COLLATE NOCASE",
            (email,),
        ).fetchone()
        if taken is not None:
            raise HTTPException(status_code=409, detail="An account with that email already exists.")
        cursor = connection.execute(
            """
            INSERT INTO users (name, email, password_hash, first_name, last_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                f"{first_name} {last_name}",
                email,
                hash_password(body.password),
                first_name,
                last_name,
            ),
        )
        connection.commit()
        row = user_by_id(connection, int(cursor.lastrowid))
    finally:
        connection.close()
    if row is None:
        raise HTTPException(status_code=500, detail="The account could not be saved.")
    start_session(response, row["id"])
    return public_user(row)


@app.post("/api/auth/login")
def login(body: LoginRequest, response: Response) -> dict:
    email = body.email.strip().lower()
    connection = connect()
    try:
        row = connection.execute(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
            (email,),
        ).fetchone()
    finally:
        connection.close()
    stored_hash = row["password_hash"] if row is not None else DUMMY_PASSWORD_HASH
    if row is None or not verify_password(body.password, stored_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    start_session(response, row["id"])
    return public_user(row)


@app.post("/api/auth/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def current_account(request: Request) -> dict:
    row = user_from_request(request)
    return {"user": public_user(row) if row is not None else None}


@app.get("/api/chat/history")
def chat_history(request: Request) -> dict:
    row = user_from_request(request)
    if row is None:
        return {"messages": []}
    return {"messages": list_chat(int(row["id"]))}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    from agent import answer_shopper
    from tools import ConfigError

    row = user_from_request(request)
    customer = None
    history = None
    user_id = None
    if row is not None:
        user_id = int(row["id"])
        customer = CustomerProfile(
            name=row["name"] or "",
            first_name=row["first_name"] or "",
            email=row["email"] or "",
        )
        history = recent_turns(user_id)
    hint = body.page
    page = page_view(hint.path if hint else "", hint.product_id if hint else None)
    try:
        reply = await answer_shopper(
            body.message.strip(),
            customer=customer,
            page=page,
            history=history,
        )
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if user_id is not None:
        save_turn(user_id, body.message.strip(), reply.message, reply.products)
    return reply


app.mount(
    "/media/products",
    StaticFiles(directory=products_dir()),
    name="product-images",
)
