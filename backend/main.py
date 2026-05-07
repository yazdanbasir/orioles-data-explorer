import sqlite3
import math
import os
import re
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/orioles.db")

VALID_TABLES = {"games", "teams", "players", "pitches", "at_bats"}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


# ── Endpoints ─────────────────────────────────────────────────────────────────

TABLE_ORDER = ["teams", "players", "games", "pitches", "at_bats"]

@app.get("/api/tables")
def list_tables():
    return TABLE_ORDER


@app.get("/api/schema")
def get_schema():
    con = get_db()
    schema = {}
    for table in VALID_TABLES:
        cur = con.execute(f"PRAGMA table_info({table})")
        schema[table] = [{"name": row["name"], "type": row["type"]} for row in cur.fetchall()]
    con.close()
    return schema


@app.get("/api/tables/{table}")
def get_table_data(
    table: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    sort: str = Query(None),
    dir: str = Query(None, pattern="^(asc|desc)$"),
):
    if table not in VALID_TABLES:
        raise HTTPException(status_code=404, detail="Table not found")

    con = get_db()

    # Validate sort column against actual columns
    columns = [row["name"] for row in con.execute(f"PRAGMA table_info({table})").fetchall()]
    order_clause = ""
    if sort and sort in columns and dir in ("asc", "desc"):
        order_clause = f"ORDER BY \"{sort}\" {dir.upper()}"

    total = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    pages = math.ceil(total / limit)
    offset = (page - 1) * limit

    rows = con.execute(
        f"SELECT * FROM {table} {order_clause} LIMIT ? OFFSET ?", (limit, offset)
    ).fetchall()

    con.close()

    return {
        "rows": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "pages": pages,
        "columns": columns,
    }


# ── Text-to-SQL ───────────────────────────────────────────────────────────────

SCHEMA_PROMPT = """
CREATE TABLE teams (
    team_id INTEGER PRIMARY KEY, name TEXT, abbreviation TEXT, league TEXT, division TEXT
);
CREATE TABLE players (
    player_id INTEGER PRIMARY KEY, full_name TEXT, birth_date TEXT,
    position TEXT, bats TEXT, throws TEXT,
    strike_zone_top REAL, strike_zone_bottom REAL
);
CREATE TABLE games (
    game_pk INTEGER PRIMARY KEY, date TEXT, season INTEGER, game_type TEXT,
    home_team_id INTEGER, away_team_id INTEGER,
    venue_name TEXT, home_score INTEGER, away_score INTEGER,
    day_night TEXT, attendance INTEGER, duration_minutes INTEGER
);
CREATE TABLE pitches (
    id INTEGER PRIMARY KEY, game_pk INTEGER, at_bat_index INTEGER,
    pitch_number INTEGER, pitcher_id INTEGER, batter_id INTEGER,
    pitching_team_id INTEGER, batting_team_id INTEGER,
    inning INTEGER, half_inning TEXT, balls INTEGER, strikes INTEGER, outs INTEGER,
    pitch_type TEXT, pitch_type_desc TEXT,
    start_speed REAL, end_speed REAL, zone INTEGER,
    spin_rate REAL, spin_direction INTEGER,
    pfx_x REAL, pfx_z REAL, px REAL, pz REAL, extension REAL, plate_time REAL,
    call_code TEXT, call_description TEXT,
    is_strike INTEGER, is_ball INTEGER, is_in_play INTEGER, is_out INTEGER,
    launch_speed REAL, launch_angle REAL, hit_distance REAL, trajectory TEXT,
    hit_location TEXT, hit_coord_x REAL, hit_coord_y REAL,
    result_event TEXT, result_description TEXT
);
CREATE TABLE at_bats (
    id INTEGER PRIMARY KEY, game_pk INTEGER, at_bat_index INTEGER,
    inning INTEGER, half_inning TEXT,
    batter_id INTEGER, pitcher_id INTEGER, batting_team_id INTEGER, pitching_team_id INTEGER,
    bat_side TEXT, pitch_hand TEXT,
    result_event TEXT, result_event_type TEXT, result_description TEXT,
    rbi INTEGER, is_out INTEGER, is_scoring_play INTEGER,
    pitch_count INTEGER, men_on_base TEXT, outs_before INTEGER
);

Key relationships:
- pitches.game_pk → games.game_pk
- pitches.pitcher_id → players.player_id
- pitches.batter_id → players.player_id
- pitches.pitching_team_id / batting_team_id → teams.team_id
- at_bats.game_pk → games.game_pk
- at_bats joins pitches via (game_pk, at_bat_index)
- games.home_team_id / away_team_id → teams.team_id

--- WHICH TABLE TO USE ---

Use `at_bats` for anything about the OUTCOME of a plate appearance:
  home runs, hits, strikeouts, walks, RBI, batting average, OBP, OPS,
  K%, BB%, plate appearances, "did the at-bat end in X"

Use `pitches` for anything about an INDIVIDUAL PITCH:
  velocity, spin rate, zone, pitch type, exit velocity, launch angle,
  break, plate location, "what did the pitch do"

Use BOTH joined when the question spans pitch characteristics AND outcomes:
  e.g. "strikeout rate on fastballs" needs pitches (pitch_type) + at_bats (result)
  Join via: at_bats.game_pk = pitches.game_pk AND at_bats.at_bat_index = pitches.at_bat_index

--- TEAM DIRECTION ---

pitching_team_id = the team whose pitcher threw the pitch (the THROWING team)
batting_team_id  = the team whose batter faced the pitch (the RECEIVING team)

"Team X allowed hard pitches" → batters from Team X faced them → filter batting_team_id
"Team X threw hard pitches"   → pitchers from Team X threw them → filter pitching_team_id

--- COUNTING STATS ---

Batting average  = H / AB
  H  = result_event_type IN ('single','double','triple','home_run')
  AB = result_event_type IN ('single','double','triple','home_run','strikeout',
       'field_out','grounded_into_double_play','double_play','triple_play',
       'fielders_choice','fielders_choice_out','force_out')
  Never use AVG() on a 0/1 flag for batting average — use SUM(H)/SUM(AB)

Strikeout rate   = strikeouts / plate_appearances (all at_bats rows)
  strikeouts = result_event_type IN ('strikeout','strikeout_double_play')

Walk rate        = walks / plate_appearances
  walks = result_event_type IN ('walk','intent_walk')

--- OTHER RULES ---

- Pitch velocity: start_speed (mph). Exit velocity: launch_speed (mph).
- ZONE: zone IN (1,2,3)=TOP, IN (4,5,6)=MIDDLE, IN (7,8,9)=BOTTOM. Use IN lists, not BETWEEN.
- PITCH TYPE: only filter by pitch_type when question explicitly says a pitch type.
  Fastballs = pitch_type IN ('FF','FT','FC'). Never use pitch_type_desc for filtering.
- Seasons available: 2024 and 2025.
- AGE: always use (julianday(date_string) - julianday(birth_date)) / 365.25
- INTEGER DIVISION: SQLite integer/integer = integer (truncated). Always cast ratios:
  use SUM(...) * 1.0 / NULLIF(SUM(...), 0) — never plain integer division for averages/rates
- NULL STATCAST FIELDS: spin_rate, start_speed, launch_speed are frequently NULL.
  Always add WHERE spin_rate IS NOT NULL (or the relevant field) when grouping or averaging them.
  Also exclude NULL pitch_type rows when grouping by pitch type.
- Minimum sample sizes: HAVING COUNT(*) >= 10 for pitch averages, >= 50 for batter exit velocity stats
- Qualifying hitter threshold: >= 50 balls in play (launch_speed IS NOT NULL)

--- PERCENTILE PATTERN ---
Always use this structure (batter_id lives on pitches, not players):
  WITH all_players AS (
    SELECT pit.batter_id, AVG(pit.launch_speed) AS avg_val
    FROM pitches pit
    JOIN players pl ON pl.player_id = pit.batter_id
    JOIN games g ON g.game_pk = pit.game_pk
    WHERE [filters] AND pit.launch_speed IS NOT NULL
    GROUP BY pit.batter_id HAVING COUNT(*) >= 50
  ),
  ranked AS (SELECT *, PERCENT_RANK() OVER (ORDER BY avg_val) AS percentile FROM all_players)
  SELECT pl.full_name, ROUND(avg_val,1), ROUND(percentile*100,1) AS percentile
  FROM ranked JOIN players pl ON ranked.batter_id = pl.player_id
  WHERE pl.full_name = 'Player Name'
"""

class QueryRequest(BaseModel):
    question: str
    previous_question: str | None = None
    previous_sql: str | None = None

@app.post("/api/query")
def natural_language_query(req: QueryRequest):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    context = ""
    if req.previous_question and req.previous_sql:
        context = f"""Previous question: {req.previous_question}
Previous SQL (use this as context if the current question references prior results):
{req.previous_sql}

"""

    prompt = f"""You are a SQL expert working with a SQLite database of MLB baseball statistics.

Schema:
{SCHEMA_PROMPT}

Rules:
- Return ONLY a valid SQLite SELECT statement, nothing else
- No markdown, no code fences, no explanation
- Never use DROP, DELETE, INSERT, UPDATE or any destructive statement
- Use only tables and columns defined in the schema above
- Always use JOIN with players or teams to resolve IDs to names where helpful
- If the question references "those players/pitchers/hitters", use the previous SQL as context to identify who they are
- If the question cannot be answered from this schema, return exactly:
  SELECT 'Cannot answer this question from the available data' AS message

{context}Question: {req.question}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=512,
    )

    raw = response.choices[0].message.content.strip()

    # Strip wrapping quotes only if the whole response is quoted
    sql = raw
    if (sql.startswith('"') and sql.endswith('"')) or \
       (sql.startswith("'") and sql.endswith("'")):
        sql = sql[1:-1]
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql).strip()

    # Safety: only allow SELECT statements and CTEs (WITH ... SELECT)
    stripped = sql.upper().lstrip()
    if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed.")

    try:
        con = get_db()
        cur = con.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = [list(r) for r in cur.fetchall()]
        con.close()
        return {"sql": sql, "columns": columns, "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL error: {str(e)}\n\nGenerated SQL:\n{sql}")
