# AI Prompts Log — HW4 (Campus Customs Shop)

A record of the prompts I typed into Cursor while building this assignment, in the order I sent them. This file is the vibe-coder log. It is not the runtime agent prompt at `backend/prompts/prompt.md`.

Every section has the problem number and title, at least one prompt I typed, and a follow-up prompt when I needed one to fix something. Titles for Problems 2–13 are filled in when each problem is started.

---

## Setup — workspace and ground rules

### Prompt typed

> Use this HW4 folder as the active directory for this hw assignment. Today we'll build a Campus Customs shop website with a chatbot. We will use a React + Vite TypeScript frontend and Python FastAPI backed with a PydanticAI agent as the "brain". The website should allow customers to browse products, create an account, chat about merch, see matching items appear on the page, and get honest answers about price/stock from a local database.
>
> For now, just set up a virtual environment like the other hw assignments. I will then provide prompts for each of the 13 problems in this hw

> Additional context before we start the problems:
> - campus_customs.db has the relevant database for product/user info
> - yalebulldogblue.com provides the style for the Campus Customs page and information for the agent prompt
> - Use the portkey api key for agent's AI calls
> - In the end, we will push the project to public GirHub repo and submit the repo URL on Canvas with the attached file structure; DO NOT commit the database or product images when we do so
>
> *(attached: screenshot of the required repo layout)*

### Follow-up prompt

N/A — no correction was needed. The second message added ground rules before the problems started.

### Result

Created `.venv` with Python 3.12.10 (same interpreter as HW 3) and upgraded pip. Confirmed `data/data/campus_customs.db` (`catalogue`, `inventory`, `users`, `chat_messages`) and that `PORTKEY_API_KEY` lives in the course-root `.env`. Agent calls will use the Portkey gateway, same pattern as HW 2 and HW 3. The database and product images stay out of the public repo. Did not scaffold the app yet.

Target layout from the screenshot:

```
hw4/
├── AI_prompts.md
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── frontend/                 # Vite React TypeScript app
├── backend/
│   ├── main.py               # FastAPI app — uvicorn main:app --reload
│   ├── agent.py
│   ├── models.py
│   ├── tools.py
│   └── prompts/
│       └── prompt.md
└── output/
    ├── harness.md
    ├── design.md
    ├── usability.md
    ├── app_check.html
    ├── app_check_images/     # screenshots linked from app_check.html
    └── audit_trail.json
```

---

## Problem 1 — Vibe coder prompts

### Prompt typed

> For Problem 1 (Vibe coder prompts), create AI_prompts.md to log what I type into the vibe coder, with sections for each problem, and a first section for the set-up prompts I've already sent

### Follow-up prompt

> Each section should problem number and title, at least one prompt I typed, and follow-up prompt if I needed it to fix something

### What the follow-up fixed

The first draft had a section per problem, but it did not give every section the same three fields: number and title, the prompt I typed, and a follow-up when one was needed.

---

## Problem 2 — Analyze the database

### Prompt typed

> For problem 2 (Analyze the database), provide an overviews of the tables and fields in data/campus_customs.db to help me understand the DB schema, esp the catalogue, inventory, and users tables.
>
> Then, start an output/harness.md file. For now, write down each table and its fields, along with one short line on why each field matters for the shop or chatbot. Show me this so I can review and tweak if needed

> Can you show me an E-R diagram for those tables to help me understand

### Follow-up prompt

N/A — the diagram was an extra view of the same schema, not a correction.

### Result

Wrote `output/harness.md` from the live schema in `data/data/campus_customs.db` (the zip unpacked one folder deeper than `data/campus_customs.db`). Covered `catalogue`, `inventory`, `users`, and `chat_messages`.

---

## Problem 3 — Build the Campus Customs website

### Prompt typed

> For Problem 3 (Build the Campus Customs website), scaffold a React + Vite + TypeScript frontend for Campus Customs. Put a nav bar at the top that links to the main pages: Home; Products; About Us; Log in; Create Account.
>
> Pull the Campus Customs-style wording from yalebulldogblue.com for Hom and About Us, but write in your own words (don't plagiarize the site's text).
>
> On the Products page, show product images from the catalogue in the DB, using the image paths in the DB, along with basic product info (eg, name, price, short description).
>
> Each product should open to a single-item page, with a large image on one side, full product text on the other (eg, description, price, sizes/stock when you havee them). Clicking on a card on Products should take the shopper there.
>
> Also, add a chat interface in the bottom right of the site (floating chat panel). For now, it doesn't need to talk to the agent; just make it a stub that can call the backend later for this hw problem.
>
> We will need a small API to read the database. For now, start a simple FastAPI app in backend/main.py just to serve products/images. We will expand on this backend in Problem 5

### Follow-up prompt

> For the colors on each individual product page, make it a dropdown with All Colors and indiividual colors, and update the sizes in stock based on the selected color

> Also make the font on the website title banner look nicer, it's very plain

### What the follow-up fixed

The product page listed colors as plain text. It now has a color dropdown. Size counts still come from `inventory`, which has no color column, so choosing a color does not invent a second stock number. The navy title banner and the Campus Customs wordmark were Arial; they now use Cormorant Garamond.

---

## Problem 4 — Create account and login

### Prompt typed

> For Problem 4 (Create account and login), build a normal create-account login flow:
> - Create account: first name, last name, email, password (including confirm password if possible)
> - Log in: email and password
>
> New accounts go in the users table. Make sure to store password securely so hackers can't access (eg, hashing, salting, etc.).
>
> To test, use the test user already in the seed DB (email: test@campuscustoms.yale.edu, pw: password). Confirm you can log in as that user and that a brand-new account you create also works.
>
> Also, update the output/harness.md with how authorization works (ie, what you store for a user and what techniques you use to protect passwords)

### Follow-up prompt

N/A

---

## Problem 5 — PydanticAI agent backend

### Prompt typed

> For problem 5 (PydanticAI agent backend), build the shop chatbot as a PydanticAI agent behind FastAPI, plugged into the front-end chat widget. Put the API app in backend/main.py (the file you run with Uvicorn). Keep the agent as these four files next to it (like in HW3):
> - backend/prompts/prompt.md: system prompt (we will grow it later)
> - backend/agent.py: agent entry/wiring
> - backend/tools.py: tools the agent can call
> - backend/models.py: Pydantic/PydanticAI structured types
>
> In main.py, expose a chat route so a message from the website returns a reply from the agent (and anything else you need for products/auth). The agent will need the AI model API key.
>
> In prompt.md, put Campus Customs voice and basic safety rules (we will expand these later).
>
> Start/update types in models.py for chat replies / product cards as needed
>
> Update harness.md to note how frontend talks to the FastAPI backend and how the agent is loaded (ie, prompt file and model).
>
> Make sure the backend runs from backend/ folder with the following terminal command:
> uvicorn main:app --reload --port 8000

### Follow-up prompt

N/A

---

## Problem 6 — Tools: product info and stock

### Prompt typed

> For problem 6 (Tools: product info and stock), make tools for the agent to look up relevant info from the DB, including product descriptions, price, and number of units in stock (including by size, when customer asks)
>
> Agent must use the database; DO NOT invent prices/quantities. If a size is out of stock, state this clearly to the user.
>
> Expand prompts.md so the agent knows it can call these tools for stock and price questions. Add/update return types in models.py. In harness.md, list each tool and explain which model fields you chose for lookup results and why. Show me the updated harness.md once you do

### Follow-up prompt

N/A

---

## Problem 7 — Chat search that updates the page

### Prompt typed

> For Problem 7 (Chat search that updates the page), add a feature for the agent if it gets asked about a type of item (eg, "what hoodies do you have?") to search the catalogue and have the website dynamically show thsoe matching items as product cards (image, name, price, short info).
>
> This is an API contract: the agent returns structured product matches and then the frontend renders them on the website.
>
> After the dynamic product codes are loaded by this new feature, ensure that the same single-item page behavior built in Problem #3 still works (ie, that each product card, including the ones the chat just put on the page, still open the detail view with large image + full description when clicked).
>
> Update prompt.md and harness.md to make it clear how search results reach the page

### Follow-up prompt

N/A

---

## Problem 8 — Customer memory

### Prompt typed

> For Problem 8 (Customer memory), set up functionality for logged-in customers so that their chat history is saved in an appropriate table in the database and is reloaded when they return.
>
> The agent should know who is chatting (eg, name, email), and put that in agents deps (or equivalent clear pattern) and know the tools the agent can call. Also make sure it passes enough page context so that questions like “do you have this in pink?” have the context of what the user is looking at. You can put code into the agent context to assist with this
>
> Note: while guests can still chat, history only needs to persist for logged-in users.
>
> Document this functionality in harness.md, including how user chat history is stored, what customer fields the agent sees, and how page context is passed

### Follow-up prompt

N/A

---

## Problem 9 — Usability improvements

### Prompt typed

> For problem 9 (Usability improvements), let’s implement 2 front end and 2 agent/backend usability improvements. The two frontend improvement should be the two improvements I recommended earlier: (1) improvement to the store name header on each page to not just be plain text; and (2) the dropdown option for colors, with dynamic updating showing how much is in stock for each size for that color of the product.
>
> For backend improvements, offer some ideas that make the agent output better, more accurate, or safer. These could be new tools for the agent or improvement to make the agent run faster/cheaper.
>
> Once you give me options for backend improvements, I will pick 2 to implement and give you the next steps in this problem 9

### Follow-up prompt

> Remove the dropdown since inventory doesn't break out quantities by color. Instead update the frontend by adding a search bar feature on the Products page. This will be the second frontend improvement
>
> For the backend improvements, add #1 and #2 from the list you gave me
>
> Also, for the Home page, get rid of text that isn't relevant to a customer (ie, "Each card uses the image path stored with that product, not a stand-in picture"). The home page should be customer-facing and encourage customers to buy products by talking about quality, range of offerings, etc.

---

## Problem 10 — Style the website

### Prompt typed

> For Problem 10 (Style the website), let's add some creative design tho the site so it feels like a real Campus Customs storefront. That includes fonts, color, hierarchy, motion, product presentation, and chat feel. Make it cohesive and professional, but also creative and fun. Don't have excess whitespace or bland aesthetic. Maybe add a parallax scrolling effect with a background image

### Follow-up prompt

> The background image in blue should be school themed like students walking, or the Yale mascot
>
> Get rid of the parallax effect, and make the characters real people, not cartoons
>
> Also change the font on the home page because the F in from looks terrible
>
> To finish Problem 10, write output/design.md, noting what we changed and why it should help the customers stick around and buy. Make it short and direct

---

## Problem 11 — Site testing (app check)

### Prompt typed

> For problem 11 (Site testing (app check)), test the live site and document it in output/app_check.html (a page you can double-click to open).
>
> Include clear screenshots and short captions for the following:
> 1. Chat checking the inventory level of item (demonstrate honest, not invented, stock/price from DB)
> 2. Dynamic search-result cards appearing after a category question (eg, hoodies)
> 3. One of the usability features I added in problem 9 (the product page search bar)
>
> Make the HTML easy to grade. It should have a header for each check, the relevant screenshot, and 1-2 sentences describing what the screenshot proves.
>
> Put the screenshot image files in output/app_check_images/ and link them from app_check.html using relative paths (eg, app_check_images/inventory.png)

### Follow-up prompt

N/A

---

## Problem 12 — Audit trail, safety, finish harness

### Prompt typed

> For problem 12 (Audit trail, safety, finish harness), keep an append-only audit trail at output/audit_trail.json recording agent-loop activity (time, tool name, short args, result, stop reason). Do not wipe it between runs.
>
> Also, create some safety rules preventing misuse of the agent, including guardrails for cost, prompt injections, etc and anything else you can think of.
>
> Finish output/harness.md, making it clear how the system works, including the following:
> - Model fields in models.py and why we chose them
> - Tools and abilities
> - Safety rules
> - Specs (loop limits, result caps, models, how to run frontend/backend)

### Follow-up prompt

N/A

---

## Problem 13 — Push to GitHub and submit the URL

### Prompt typed

> For problem 13 (Push to GitHub and submit the URL), put the code in a folder named hw4 and push it to my public GitHub repository. I will submit the repo URL (the link graders can open and clone).
>
> DO NOT put my real .env in the upload or any other secrets. Also do not include the campus_customs.db or product images in the GitHub repo. Use .gitignore and include a .env.example file with placeholders only.
>
> The expected file layout should look like the attached image.
>
> Confirm that the agent itself is four files under backend/ (prompts/prompt.md, agent.py, tools.py, and models.py). The README.md should explain how to run the frontend and backend after the grader places their data pack.
>
> Before you push to GitHub, make sure everything works and double-check that no secrets get included in files pushed to GitHub

### Follow-up prompt

N/A

### Result

Public repo: https://github.com/brian-casey98/hw4
