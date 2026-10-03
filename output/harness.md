# Harness — Campus Customs

Working notes for how the shop and chatbot are built. This section records the database as it exists now, and why each field matters.

The file on disk is `data/data/campus_customs.db` (the zip unpacked one folder deeper than `data/campus_customs.db`). Four application tables: `catalogue` (102 products), `inventory` (612 size rows), `users` (3 accounts), and `chat_messages` (22 saved turns). `inventory.product_id` points at `catalogue.product_id`. `chat_messages.user_id` points at `users.id`. Every product has exactly six size rows, and every inventory row matches a catalogue product.

## catalogue

One row per product the shop can show and the chatbot can recommend.

| Field | Why it matters |
| --- | --- |
| `product_id` | Stable slug (`2025-yale-vs-harvard-t-shirt`) that ties a product to its image, sizes, and any chat match. |
| `name` | The title customers see on a product card and in a chat reply. |
| `garment_type` | Lets the shop filter, and the chatbot answer, by kind of item (hoodie, crewneck, t-shirt, jacket). |
| `description` | The sentence the chatbot uses when someone asks what a piece looks like or what is printed on it. |
| `colors` | JSON list of color names on the piece. Inventory has no color column, so a color does not have its own size counts. The product page lists the names. The assistant uses `check_color` for a yes or no. |
| `search_tags` | JSON list of extra words (college, sport, "The Game") the chatbot can match when the customer does not use the product name. |
| `image_file_path` | Relative path such as `products/basic-hoodie-big-yale.jpg`, so the page can show the photo next to a match. |
| `price` | Dollar price the chatbot must quote from the database rather than invent. |

## inventory

One row per product and size. Sizes are XS, S, M, L, XL, and XXL. `quantity` is how many are left; 145 rows are already at 0, and no product is out of stock in every size.

| Field | Why it matters |
| --- | --- |
| `id` | Row key for a single size of a single product. |
| `product_id` | Joins this size back to the catalogue item the customer is looking at. |
| `size` | The size a shopper asks for, so the page and the chatbot can say whether that size exists. |
| `quantity` | Units on hand for that size of the whole piece, not for one color. A reply about stock has to come from this number, including when it is zero. |

## users

Accounts for sign-in and for tying chat history to a person. `name` currently equals `first_name` plus `last_name` on all three rows. `first_name` and `last_name` were added after the original columns and are allowed to be empty.

| Field | Why it matters |
| --- | --- |
| `id` | The account key that chat history attaches to. |
| `name` | The display name already stored as one string ("Ada Lovelace"). |
| `email` | Unique login name. No two accounts can share an email. |
| `password_hash` | Stored password check only. The shop never keeps or shows the raw password. See Authorization below. |
| `created_at` | When the account was created, useful if we need to tell accounts apart later. |
| `first_name` | Given name for a greeting or a new signup form. |
| `last_name` | Family name, paired with `first_name` when an account is created. |

## chat_messages

Saved turns for a signed-in user. There are 11 user messages and 11 assistant replies. Only assistant rows carry `products_json`. User 2 (Ada Lovelace) has no saved chat.

| Field | Why it matters |
| --- | --- |
| `id` | Orders and identifies a single saved message. |
| `user_id` | Whose conversation this turn belongs to, so one customer does not see another's chat. |
| `role` | `user` or `assistant`, so the transcript can be replayed in order. |
| `content` | The words that were said. This is what the page shows in the thread. |
| `products_json` | On assistant turns, the matching products (catalogue fields plus `image_url`, per-size `inventory`, and `total_stock`) that the page should render beside that reply. Empty on user turns. |
| `created_at` | When the turn was saved, so history stays in time order. |

## Authorization

A shopper account stores `id`, `name` (first and last joined), `email`, `password_hash`, `created_at`, `first_name`, and `last_name`. The password itself is not stored.

`password_hash` looks like `pbkdf2_sha256$<salt>$<hex digest>`.

- The digest is PBKDF2-HMAC-SHA256, 120,000 iterations. That is the count that verifies the seed account `test@campuscustoms.yale.edu`.
- Each new account gets its own salt from `secrets.token_hex(8)`. The salt is not secret; it stops one stolen hash from being reused against another account. It is stored in the hash string because the check needs it.
- Login compares the new digest to the stored one with `hmac.compare_digest`, so the check does not stop early when a guess is wrong.
- A failed login says "Email or password is incorrect" either way. A missing email is still checked against a throwaway hash, so the response does not give the address away by returning faster.

After a successful login or signup, the API sets an httpOnly cookie named `campus_session`. The cookie holds a user id and an expiry (7 days), signed with HMAC-SHA256. JavaScript on the page cannot read it. The signing key is created in `backend/.session_secret` and is not committed. Log out deletes the cookie.

## Shop assistant

The chat panel sends `POST /api/chat` with `{ "message": "..." }`. In development, Vite proxies `/api` and `/media` to `http://127.0.0.1:8000`, so the browser talks to the FastAPI app as if it were the same site. Run that app from the `backend/` folder:

```
uvicorn main:app --reload --port 8000
```

`backend/main.py` keeps the product and account routes and adds the chat route. The route calls `answer_shopper` in `backend/agent.py`.

The agent is a PydanticAI `Agent`. Its instructions are the text of `backend/prompts/prompt.md`, read when the agent module loads. The model name is `OPENAI_MODEL`. On each chat call the app fills any unset variable from `backend/.env`, then the HW4 `.env`, then the course-root `.env`, and it skips blank values. Nothing in the code names a model. The course `.env` leaves `OPENAI_MODEL` empty, so the HW4 `.env` (gitignored) sets it to `gpt-5.6-sol`. Calls use the OpenAI SDK pointed at Portkey (`https://api.portkey.ai/v1`) with `PORTKEY_API_KEY` from the course `.env`. If the model or the key is missing, `/api/chat` returns that reason instead of guessing.

`backend/tools.py` is what the agent can call. Every price and every unit count below is read from `campus_customs.db` on that call. The agent returns a `ChatReply` (the words, plus product ids). The API then loads those ids into `ProductCard`s from the database, so the photo and the size counts on the card are the stored ones, not numbers the model typed. The panel shows the reply and those cards.

## Lookup tools

Four tools. Search only identifies a piece. Description and price come from a second call. A color yes or no comes from `check_color`. Size counts come from `get_stock`. Splitting them keeps a price from being quoted off a search list, and keeps a sold-out size visible as its own field.

### `search_products`

Finds up to 40 catalogue rows. A word has to appear in the name, garment type, search tags, description, or colors. "hoodies" is also tried as "hoodie". A hit in the name or garment type outranks a mention buried in the description, and those stronger hits are the ones returned when any exist.

Return type: `ProductMatch`.

| Field | Why it is on the result |
| --- | --- |
| `product_id` | The slug the next tools require. The chat card is loaded with this same id. |
| `name` | The title to show the customer, taken from `catalogue.name`. |
| `garment_type` | Separates a hoodie from a t-shirt when the names share words like "Yale". |

Price and quantity are left off this result so those numbers have to come from `get_product_info` and `get_stock`.

### `get_product_info`

Reads one `catalogue` row. Used for "what is this?" and "how much?"

Return type: `ProductInfo`.

| Field | Why it is on the result |
| --- | --- |
| `product_id` | Confirms which row was opened. |
| `name` | The catalogue title, so the reply names the same piece the price belongs to. |
| `garment_type` | The kind of garment, from the same row as the price. |
| `description` | The stored sentence for what the piece looks like or what is printed on it. The reply is supposed to use this text rather than a guessed description. |
| `price` | `catalogue.price` in dollars. This is the only price the agent is allowed to quote. |
| `colors` | The JSON color list on the row. Names only. A yes or no about one color the customer named comes from `check_color`, not from guessing against this list in the reply. |
| `stock_note` | A fixed reminder that this result has no unit counts. The model is pointed at `get_stock` instead of filling in a number. |

### `check_color`

Reads the `catalogue.colors` list for one product and one color phrase, such as "pink" or "navy". "navy" matches a stored name that contains it, such as "navy blue". A color that is not on the list is `available: false`.

Return type: `ColorCheck`.

| Field | Why it is on the result |
| --- | --- |
| `product_id` | Confirms which catalogue row was checked. |
| `name` | The catalogue title, so the color answer stays on the right piece. |
| `asked_color` | The color words the customer used, kept separate from the stored name. |
| `available` | True only when that color is on the row. The reply is sent back if it says the opposite. |
| `matched_color` | The stored color that matched, such as "navy blue" for "navy". Empty when nothing matched. |
| `colors` | The full list on the row, so the reply can name what is actually offered. |
| `note` | Says stock is not kept per color. A color match is not a unit count. |

### `get_stock`

Reads `inventory` for one product. Optional `size` accepts words like "medium" or "M" and maps them to XS, S, M, L, XL, XXL.

Return type: `StockReport`.

| Field | Why it is on the result |
| --- | --- |
| `product_id` | Confirms which product the counts belong to. |
| `name` | The catalogue title next to the counts, so a size answer stays attached to the right piece. |
| `sizes` | Every size row. Each item is a `SizeCount`: `size` (the label the customer uses), `quantity` (units on hand for the whole piece, not per color), and `in_stock` (true only when `quantity` is above zero). All six sizes are returned so a zero is not dropped. |
| `total_stock` | Sum of those quantities, for "how many are left?" when no size was named. |
| `out_of_stock_sizes` | The size labels whose quantity is 0. A separate list, so a sold-out size is not hidden inside a long size list. |
| `asked_size` | The shop size the customer named, after "medium" is turned into `M`. Empty when they did not name a size. |
| `asked_quantity` | Units left in that size. Zero is the out-of-stock number. |
| `asked_in_stock` | False when that size has quantity 0. The reply is checked for an "out of stock" statement in that case. |
| `size_note` | Set when the word they used is not a shop size, so the agent says so instead of inventing a count. |
| `price_note` | A fixed reminder that this result has no dollar price. The model is pointed at `get_product_info`. |

Before a reply is sent, a dollar amount in the sentence (`$68` or `68 dollars`) has to equal a `price` from `get_product_info` on this turn. A size count (`5 in stock`, `only 2`, `medium is 0`) has to equal `asked_quantity`, a size `quantity`, or `total_stock` from `get_stock` on this turn. Anything else is rejected and the agent is asked to quote the tool number.

## How search results reach the page

A question such as "what hoodies do you have?" is a browse question. The agent must call `search_products` before it answers. Its reply is a `ChatReply`: the sentence in `message`, and the matching slugs in `product_ids`. For a browse question the API does not stop at the few ids named in the sentence. It runs `search_products` on the customer's message and sends that full list, in search order, so the page shows the matching pieces.

`POST /api/chat` turns those ids into `products`, a list of `ProductCard`s loaded from the database (`product_id`, `name`, `garment_type`, `description`, `price`, `image_url`, and the size rows). The prices and photos on the cards are the stored ones.

## Customer memory

Guests can still send a message. Nothing is written for them, and `GET /api/chat/history` is an empty list. A signed-in shopper is recognized from the `campus_session` cookie. Each of their turns is inserted into `chat_messages`: one `user` row with the words they typed, then one `assistant` row with the reply and `products_json` (the same product cards, as JSON). `user_id` is that account. `created_at` is the database default. When they come back, the chat panel calls `GET /api/chat/history` and shows those rows in order. The agent also receives the latest 12 saved lines as its message history, so a follow-up can refer to the earlier turn. Logging out clears the panel on this browser. The rows stay on the account.

The agent’s deps (`ShopDeps`) carry three things for the turn:

| What | Fields the agent is told |
| --- | --- |
| Customer | `name`, `first_name`, and `email` from `users`, only when the cookie matches an account. A guest has no customer. The password hash is not included. |
| Tools | The four calls it can make: `search_products`, `get_product_info`, `check_color`, and `get_stock`, each with a one-line reminder of what it returns. |
| Page | `path` from the browser. On `/products/{id}`, the server looks that id up in `catalogue` and adds `product_id`, `name`, `garment_type`, and `colors`. An unknown id is ignored. |

The chat request body is `{ message, page: { path, product_id } }`. `page_view` in `backend/tools.py` turns that into the page dep. A question such as “do you have this in pink?” uses that product as “this”: the instructions name the piece, and the prompt tells the agent to call `check_color` on that id before answering. If the customer asked whether a piece comes in a color and `check_color` was not called, the reply is not sent. Stock is still not per color. On any other path, “this” has no piece attached, so the agent is told to ask which one they mean.

The chat panel keeps that list in page state. Home and Products then draw the same `ProductCard` used for the catalogue: image, name, price, and the short description. Each card is a link to `/products/{product_id}`. That route is the Problem 3 detail page, so a card the chat just placed still opens the large photo, the full description, and the size counts. "Show the full catalogue" clears the match list and restores the usual grid.

## Model fields

`backend/models.py` is the contract between the website, the API, and the agent. Fields that are only for the model are described below. The lookup results (`ProductMatch`, `ProductInfo`, `ColorCheck`, `SizeCount`, `StockReport`) are the tool tables above: each field is there so the model can answer from the database without inventing a price, a color, or a count.

| Model | Field | Why it is there |
| --- | --- | --- |
| `RegisterRequest` | `first_name`, `last_name` | Stored on `users` and used as the greeting name. Capped at 80 characters. |
| `RegisterRequest` | `email` | The login id. Unique in `users`. |
| `RegisterRequest` | `password`, `confirm_password` | Checked as a pair, then stored only as a salted hash. Length 8–128 so a blank or a huge password never reaches the hasher. |
| `LoginRequest` | `email`, `password` | The sign-in form. The password is compared to the hash and is not kept. |
| `SizeStock` | `size`, `quantity` | One inventory row on a product card. The page draws these. The model does not type them. |
| `ProductCard` | `product_id`, `name`, `garment_type`, `description`, `price`, `colors`, `image_url`, `inventory`, `total_stock` | What the website renders after a chat match. Loaded from the database by id, so a photo or a price on the card is the stored one. |
| `ChatReply` | `message` | The sentence in the chat panel. The model writes this, and the validators reject a price or a size count that no tool returned. |
| `ChatReply` | `product_ids` | Slugs the model wants shown as cards. Ids that no tool returned are rejected. For a browse question the API replaces this list with the full search. |
| `PageHint` | `path`, `product_id` | Sent by the browser with each chat message. `path` is capped at 300 characters and `product_id` at 120, so a page hint cannot smuggle a long instruction. The server only keeps a product id that exists in the catalogue. |
| `ChatRequest` | `message`, `page` | One shopper turn. `message` must be 1–2000 characters, which caps the cost of a single question. |
| `ChatResponse` | `message`, `products` | What the chat panel receives. `products` is a list of `ProductCard`s, not the model's own numbers. |

## Tools and abilities

The agent can do four database lookups and nothing else. It cannot browse the web, run shell commands, read another customer's chat, or change a password.

| Tool | What it can do |
| --- | --- |
| `search_products` | Find up to 40 catalogue rows from the shopper's words. Returns id, name, and garment type. |
| `get_product_info` | Read one row's description and price. |
| `check_color` | Say whether a named color is on that row. |
| `get_stock` | Read the six size counts, including zeros. |

A product id passed to the last three tools has to be a catalogue slug (`basic-hoodie-big-yale`). Anything else is rejected and written to the audit trail. Search text is cut at 200 characters before it hits the database.

## Safety rules

These run in code, in `backend/safety.py` and `backend/agent.py`, with a matching section in `backend/prompts/prompt.md`.

- **Prompt injection.** A message that tells the assistant to ignore its instructions, reveal the prompt, take a new role, print an API key, or read someone else's account is refused before any model call. The shopper gets one sentence offering merchandise help. The same check strips a blocked line out of the history that is sent on a later turn, so one bad message is not replayed as an instruction.
- **Indirect injection.** The prompt tells the model that catalogue descriptions are product copy. A sentence in a description that says "ignore your rules" is not an order.
- **Other people's data.** The model is given the signed-in shopper's name and email only. No password hash, no other account, no other chat. The prompt forbids asking for or repeating a password.
- **Invented facts.** Dollar amounts have to match `get_product_info`. Size counts have to match `get_stock`. A color claim has to match `check_color`. Unknown product ids are dropped.
- **Cost.** One question may make at most 8 model requests, 6 tool calls, 16,000 tokens in total, and 2,000 output tokens. Past that, the shopper is asked to narrow the question and the model is not called again. History sent to the model is the last 12 lines, each cut to 400 characters. A reply longer than 900 characters is sent back to be shortened. The shopper's own message is already capped at 2,000 characters.
- **Scope.** Questions that are not about this shop are refused. The assistant does not reveal the prompt, the tool list, or the audit file.

## Audit trail

`output/audit_trail.json` is a JSON list. Each agent-loop step appends one object. Starting the server does not clear it, and a new question does not replace older rows.

| Field | What it records |
| --- | --- |
| `time` | UTC time of that step. |
| `tool` | `search_products`, `get_product_info`, `check_color`, or `get_stock`. Empty on the closing row. |
| `args` | A short form of the arguments, such as `product_id=basic-hoodie-big-yale size=medium`. Cut at 180 characters. |
| `result` | A short outcome, such as `5 matches` or `$98` or `qty=0`. Not the full description, and not a password. |
| `stop_reason` | Empty while tools are running. The last row of a turn is `completed`, `refused` (blocked before the model), or `usage_limit`. |

## Specs

| Limit | Value |
| --- | --- |
| Model requests per question | 8 |
| Tool calls per question | 6 |
| Total tokens per question | 16,000 |
| Output tokens per question | 2,000 |
| Shopper message | 1–2,000 characters |
| Reply length | 900 characters, then the model is asked to shorten it |
| Search results | 40 rows |
| History sent to the model | 12 lines, 400 characters each |
| Allowed models | `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`, `gpt-5.6-astra` |
| Model in use | `OPENAI_MODEL` from the HW4 `.env`. This copy uses `gpt-5.6-sol`. The code does not substitute a model if that variable is blank. |
| Provider | OpenAI SDK via Portkey at `https://api.portkey.ai/v1`, key `PORTKEY_API_KEY` in the course `.env` |

Run the API from `backend/` with the project virtualenv:

```
..\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

Run the website from `frontend/`:

```
npm run dev -- --host 127.0.0.1 --port 5173
```

The page is `http://127.0.0.1:5173/`. Vite proxies `/api` and `/media` to port 8000.
