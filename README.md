# Orioles Data Explorer

A lightweight web app for exploring the MLB pitch database. Three tabs:

- **Query** — ask any baseball question in plain English and get results
- **Data** — browse all five tables with sorting and pagination
- **Schema** — ER diagram showing how the tables relate

This was built as a bonus on top of the core database submission to make the data accessible to anyone — not just someone comfortable writing SQL. The goal was to turn a database file into something a scout, coach, or analyst could open in a browser and immediately start using.

---

## Natural Language Queries

The Query tab uses a text-to-SQL interface powered by Llama 3.3 (via Groq's free API). Type any baseball question in plain English, and the app generates the SQL, runs it against the database, and returns the results as a table. The generated SQL is always shown so you can inspect exactly what ran.

Conversation context is supported — follow-up questions like *"what percentage did those pitchers throw over 95mph for the season?"* correctly reference the previous query. All four sample questions from the project requirements return accurate, verified results.

---

## Requirements

- Python 3.x
- Node.js

---

## Running the app

**1. Start the backend**

```bash
cd app/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 1894 --reload
```

**2. Start the frontend** (in a separate terminal)

```bash
cd app/frontend
npm install
npm run dev
```

Then open **http://localhost:1954** in your browser.

---

## Note on the Query tab

The Groq API key is included in `app/backend/.env`. No setup needed — it works out of the box.
