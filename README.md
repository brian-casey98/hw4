# Campus Customs

Yale Bulldog Blue shop site for MGT 409. The page is a React app. The API and the shop assistant are Python. The assistant is a PydanticAI agent with four files:

- `backend/prompts/prompt.md` — instructions
- `backend/agent.py` — the agent loop
- `backend/tools.py` — catalogue, price, color, and stock lookups
- `backend/models.py` — request and reply shapes

`backend/main.py` is the FastAPI app. `backend/auth.py` hashes passwords and signs the session cookie. `backend/safety.py` blocks misuse and appends `output/audit_trail.json`.

The database and product photos are not in this repo. Place the course data pack locally before starting the API.

## Data pack

Unzip the pack so these paths exist inside this folder:

- `data/data/campus_customs.db`
- `data/data/products/` (the product JPEG files)

`data/campus_customs.db` and `data/products/` also work.

## Secrets

```
copy .env.example .env
```

Set `OPENAI_MODEL` to one of `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`, or `gpt-5.6-astra`. Set `PORTKEY_API_KEY` to your Portkey key. The app reads `backend/.env`, then this folder's `.env`, then a parent `.env` if one exists, and it skips blank values. It does not pick a model when `OPENAI_MODEL` is empty.

`.env` and `backend/.session_secret` are gitignored. The session file is created on first use.

## Backend

From this folder, with Python 3.12:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then, from `backend/`:

```
..\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

## Frontend

From `frontend/`:

```
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173/`. Vite sends `/api` and `/media` to port 8000.

The seed account in the data pack is `test@campuscustoms.yale.edu` / `password`.
