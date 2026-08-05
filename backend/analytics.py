"""Event store for usage analytics and education research.

Design constraints, in priority order:

1. **Never break a request.** Every call here is wrapped so a logging failure
   degrades to a dropped row, not a 500 for a student.
2. **Metadata only — never student work.** No problem text, no submitted
   working, no feedback text, no images. Everything below answers a research
   question without retaining coursework. This is what makes the difference
   between a usage log and a database of student submissions.
3. **Pseudonymous.** The client id is HMAC'd with a server-side salt before
   storage, so rows can be linked into a per-student sequence (needed for
   retention and improvement curves) without the table identifying anyone.
   With ANALYTICS_SALT unset a random per-boot salt is used, which makes
   linkage impossible across restarts — set it explicitly for a real study.
4. **Reproducible.** Rows carry schema_version so a mid-term change to what
   is collected is visible in analysis rather than silently mixed in.

> Publishing on this data involves human subjects. Get NTU IRB/ethics review
> and student notice in place *before* the term starts — retro-fitting consent
> to data already collected is usually not possible.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("captain_thermo.analytics")

SCHEMA_VERSION = 3

# On Render this should point at a mounted disk; the container filesystem is
# wiped on every deploy, which would silently discard a term of data.
DB_PATH = Path(os.getenv("ANALYTICS_DB", str(Path(__file__).resolve().parent.parent / "data" / "analytics.db")))
ENABLED = os.getenv("ANALYTICS_ENABLED", "true").lower() in ("1", "true", "yes")
_SALT = os.getenv("ANALYTICS_SALT", "").encode() or secrets.token_bytes(32)
_EPHEMERAL_SALT = not os.getenv("ANALYTICS_SALT")
# Timestamps are stored UTC (correct — unambiguous, DST-free). Reports are read
# by a person in one place, so the heat map converts on the way out.
# SQLite modifier form, e.g. "+8 hours" for Singapore.
TZ_OFFSET = os.getenv("ANALYTICS_TZ_OFFSET", "+8 hours")

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

# $/1M (input, output). Cache reads bill at 0.1x input; writes at 1.25x (5m)
# or 2x (1h) — we use the configured TTL's multiplier via cost().
PRICES = {
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

DDL = """
CREATE TABLE IF NOT EXISTS events (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ts              TEXT    NOT NULL,   -- ISO-8601 UTC
  day             TEXT    NOT NULL,   -- YYYY-MM-DD, for cheap grouping
  hour            INTEGER NOT NULL,   -- 0-23 UTC
  dow             INTEGER NOT NULL,   -- 0=Mon
  schema_version  INTEGER NOT NULL,
  student         TEXT,               -- HMAC of client id; NOT reversible
  tool            TEXT    NOT NULL,   -- chat|generate|grade|flashcards
  topic           TEXT,               -- L0..L7
  difficulty      TEXT,
  served_from     TEXT,               -- live|bank
  model           TEXT,
  -- grader signal (the pedagogically interesting part)
  verdict         TEXT,
  error_type      TEXT,
  score           INTEGER,
  concept         TEXT,               -- what the problem actually tested
  image_count     INTEGER,
  -- engagement
  turn_index      INTEGER,            -- nth turn of a chat conversation
  -- Groups turns into one conversation, and successive practice/grade events
  -- into one working session. Without it turn_index is unusable: you can count
  -- turns but not conversations, so "median turns to resolution" — the number
  -- that actually tests whether Socratic gating works — can't be computed.
  -- Cannot be retro-fitted, which is why it ships before students arrive.
  session_id      TEXT,
  -- Set when a submission follows an earlier grading of the same concept by
  -- the same student. Turns "47 conceptual errors on L4" into "conceptual
  -- errors on L4 fell 60% after one round of feedback".
  prior_event_id  INTEGER,
  prior_score     INTEGER,
  minutes_since_prior REAL,
  -- Practice: was the worked solution revealed, and how long after the problem
  -- appeared? A short delay is answer-seeking; a long one is productive
  -- struggle. Null means never opened.
  solution_revealed_after_s REAL,
  -- Student satisfaction: +1 / -1 on a piece of feedback, recorded as its own
  -- row with prior_event_id pointing at what was rated (the log stays
  -- append-only). Deliberately a rating and not free text — a comment box is
  -- student-authored prose that can carry names, matric numbers or complaints
  -- about staff, which would change the privacy posture of the whole table.
  rating          INTEGER,
  -- performance & cost
  latency_ms      INTEGER,
  cache_read      INTEGER,
  cache_write     INTEGER,
  in_tokens       INTEGER,
  out_tokens      INTEGER,
  cost_usd        REAL,
  ok              INTEGER NOT NULL DEFAULT 1,
  error_kind      TEXT                -- set when the request failed
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS ix_events_day    ON events(day);
CREATE INDEX IF NOT EXISTS ix_events_tool   ON events(tool);
CREATE INDEX IF NOT EXISTS ix_events_topic  ON events(topic);
CREATE INDEX IF NOT EXISTS ix_events_student ON events(student);
CREATE INDEX IF NOT EXISTS ix_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS ix_events_concept ON events(student, concept);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Add any columns the running code expects but an older DB lacks.

    `CREATE TABLE IF NOT EXISTS` is a no-op against an existing table, so the
    DDL above does NOT bring a v1 database up to v2 — it silently leaves the
    new columns missing. The failure then surfaces somewhere unrelated: the
    index creation raises "no such column: session_id", _connect() swallows it,
    and analytics stops recording entirely while the app looks healthy.

    That is exactly what happened on the v1 -> v2 deploy. The fix is to diff
    the live table against what the code expects and ALTER in the difference,
    which also means future column additions need no bespoke migration — add
    the column to the DDL and to the list below, and old databases catch up on
    next boot.
    """
    expected = {
        "session_id": "TEXT",
        "prior_event_id": "INTEGER",
        "prior_score": "INTEGER",
        "minutes_since_prior": "REAL",
        "solution_revealed_after_s": "REAL",
        "rating": "INTEGER",
    }
    have = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
    added = [c for c in expected if c not in have]
    for col in added:
        conn.execute(f"ALTER TABLE events ADD COLUMN {col} {expected[col]}")
    if added:
        conn.commit()
        log.info("analytics: migrated schema, added %s", ", ".join(added))


def _connect() -> sqlite3.Connection | None:
    global _conn
    if not ENABLED:
        return None
    if _conn is not None:
        return _conn
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        c.execute("PRAGMA journal_mode=WAL")      # survives an unclean restart
        c.executescript(DDL)                      # no-op if the table exists
        _migrate(c)                               # bring an older table up to date
        c.executescript(INDEXES)                  # only after columns exist
        c.commit()
        _conn = c
        if _EPHEMERAL_SALT:
            log.warning("ANALYTICS_SALT unset — student pseudonyms will not "
                        "survive a restart; set it before collecting study data")
        log.info("analytics db at %s", DB_PATH)
    except Exception as e:                        # noqa: BLE001 - never fatal
        log.error("analytics disabled, cannot open %s: %s", DB_PATH, e)
    return _conn


def pseudonym(client_id: str | None) -> str | None:
    """Stable, non-reversible per-student id."""
    if not client_id:
        return None
    return hmac.new(_SALT, client_id.encode(), hashlib.sha256).hexdigest()[:16]


def cost(model: str, usage, cache_ttl: str = "1h") -> float:
    """Dollar cost of one call from its usage block."""
    if usage is None:
        return 0.0
    pin, pout = PRICES.get(model, (3.0, 15.0))
    write_mult = 2.0 if cache_ttl == "1h" else 1.25
    return (
        (getattr(usage, "cache_read_input_tokens", 0) or 0) * 0.1 * pin
        + (getattr(usage, "cache_creation_input_tokens", 0) or 0) * write_mult * pin
        + (getattr(usage, "input_tokens", 0) or 0) * pin
        + (getattr(usage, "output_tokens", 0) or 0) * pout
    ) / 1e6


def record(**f) -> int | None:
    """Insert one event, returning its id. Drops silently on failure — never breaks a request."""
    conn = _connect()
    if conn is None:
        return None
    now = datetime.now(timezone.utc)
    row = {
        "ts": now.isoformat(timespec="seconds"),
        "day": now.strftime("%Y-%m-%d"),
        "hour": now.hour,
        "dow": now.weekday(),
        "schema_version": SCHEMA_VERSION,
        **{k: f.get(k) for k in (
            "student", "tool", "topic", "difficulty", "served_from", "model",
            "verdict", "error_type", "score", "concept", "image_count",
            "turn_index", "session_id", "prior_event_id", "prior_score",
            "minutes_since_prior", "solution_revealed_after_s", "rating",
            "latency_ms", "cache_read", "cache_write",
            "in_tokens", "out_tokens", "cost_usd", "error_kind")},
        "ok": 1 if f.get("ok", True) else 0,
    }
    cols = ",".join(row)
    try:
        with _lock:
            cur = conn.execute(
                f"INSERT INTO events ({cols}) VALUES ({','.join('?' * len(row))})",
                list(row.values()))
            conn.commit()
            return cur.lastrowid
    except Exception as e:                        # noqa: BLE001
        log.warning("analytics insert failed: %s", e)
    return None


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    conn = _connect()
    if conn is None:
        return []
    try:
        with _lock:
            cur = conn.execute(sql, params)
            keys = [d[0] for d in cur.description]
            return [dict(zip(keys, r)) for r in cur.fetchall()]
    except Exception as e:                        # noqa: BLE001
        log.warning("analytics query failed: %s", e)
        return []


def find_prior_attempt(student: str | None, concept: str | None,
                       within_hours: int = 72) -> dict | None:
    """The same student's most recent graded attempt at the same concept.

    Used to link a resubmission to what came before, so the pair can be read as
    a learning event rather than two unrelated rows. Bounded by `within_hours`
    because two attempts a month apart aren't a response to feedback — they're
    just two attempts, and treating them as a before/after pair would inflate
    any measured improvement.
    """
    if not student or not concept:
        return None
    rows = _rows(
        "SELECT id, score, ts FROM events WHERE student=? AND concept=? "
        "AND tool='grade' AND ok=1 AND score IS NOT NULL "
        "ORDER BY id DESC LIMIT 1", (student, concept))
    if not rows:
        return None
    prior = rows[0]
    try:
        then = datetime.fromisoformat(prior["ts"])
        mins = (datetime.now(timezone.utc) - then).total_seconds() / 60
    except (ValueError, TypeError):
        return None
    if mins > within_hours * 60:
        return None
    return {"prior_event_id": prior["id"], "prior_score": prior["score"],
            "minutes_since_prior": round(mins, 1)}


def _observation_window() -> dict:
    """How long the tool has been running, and how many of each weekday fell in it.

    The per-week average heat map needs a divisor per weekday, and the obvious
    choices are both wrong. Dividing by 16 assumes a full term that may not have
    elapsed; dividing by "days that had activity" drops quiet days out of the
    denominator, so a Monday with no usage makes the remaining Mondays look
    busier. The correct divisor is how many Mondays *occurred* in the window,
    whether or not anyone used the tool on them.
    """
    row = _rows("SELECT MIN(date(ts, ?)) a, MAX(date(ts, ?)) b FROM events WHERE ok=1",
                (TZ_OFFSET, TZ_OFFSET))
    if not row or not row[0].get("a"):
        return {"window": None, "weekday_counts": {}}
    try:
        start = datetime.strptime(row[0]["a"], "%Y-%m-%d").date()
        end = datetime.strptime(row[0]["b"], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return {"window": None, "weekday_counts": {}}

    days = (end - start).days + 1
    counts = {d: 0 for d in range(7)}
    for i in range(days):
        counts[(start.toordinal() + i - 1) % 7] += 1      # 0 = Monday
    return {
        "window": {"start": row[0]["a"], "end": row[0]["b"],
                   "days": days, "weeks": round(days / 7, 1)},
        "weekday_counts": counts,
    }


def summary() -> dict:
    """Aggregates for the dashboard and for sharing with colleagues."""
    total = _rows("SELECT COUNT(*) n, COUNT(DISTINCT student) students, "
                  "ROUND(SUM(cost_usd),2) spend FROM events WHERE ok=1")
    # Health of the collection itself. Both of these fail silently in ways that
    # only become visible when you go to analyse a term of data and find it
    # missing or unlinkable, so surface them where they'll be noticed.
    on_disk = str(DB_PATH).startswith("/var/data") or str(DB_PATH).startswith("/data")
    warnings = []
    if not ENABLED:
        warnings.append("ANALYTICS_ENABLED is false — nothing is being recorded.")
    if _conn is None and ENABLED:
        warnings.append(f"database could not be opened at {DB_PATH} — nothing is being recorded.")
    if not on_disk:
        warnings.append(
            f"database is at {DB_PATH}, which is NOT a mounted disk — on Render this "
            "is wiped on every deploy. Set ANALYTICS_DB=/var/data/analytics.db and "
            "confirm the disk is attached.")
    if _EPHEMERAL_SALT:
        warnings.append(
            "ANALYTICS_SALT is unset — student pseudonyms regenerate on every "
            "restart, so retention and improvement analysis will be wrong.")
    return {
        "totals": total[0] if total else {},
        "schema_version": SCHEMA_VERSION,
        "collection": {"db_path": str(DB_PATH), "on_persistent_disk": on_disk,
                       "enabled": ENABLED, "stable_pseudonyms": not _EPHEMERAL_SALT,
                       "warnings": warnings},
        "by_tool": _rows("SELECT tool, COUNT(*) n, COUNT(DISTINCT student) students, "
                         "ROUND(SUM(cost_usd),2) spend, ROUND(AVG(latency_ms)) avg_ms "
                         "FROM events WHERE ok=1 GROUP BY tool ORDER BY n DESC"),
        # The headline research output: where students actually go wrong.
        "misconceptions": _rows(
            "SELECT topic, error_type, COUNT(*) n, ROUND(AVG(score),2) avg_score "
            "FROM events WHERE tool='grade' AND ok=1 AND error_type IS NOT NULL "
            "AND error_type != 'none' GROUP BY topic, error_type ORDER BY n DESC"),
        "concepts": _rows(
            "SELECT topic, concept, COUNT(*) n, ROUND(AVG(score),2) avg_score "
            "FROM events WHERE tool='grade' AND ok=1 AND concept IS NOT NULL "
            "GROUP BY topic, concept HAVING n >= 2 ORDER BY avg_score ASC LIMIT 25"),
        "by_topic": _rows("SELECT topic, COUNT(*) n, COUNT(DISTINCT student) students "
                          "FROM events WHERE ok=1 AND topic IS NOT NULL "
                          "GROUP BY topic ORDER BY topic"),
        "by_day": _rows("SELECT day, COUNT(*) n, COUNT(DISTINCT student) students, "
                        "ROUND(SUM(cost_usd),2) spend FROM events WHERE ok=1 "
                        "GROUP BY day ORDER BY day"),
        "by_hour": _rows("SELECT hour, COUNT(*) n FROM events WHERE ok=1 "
                         "GROUP BY hour ORDER BY hour"),

        # Day x hour heat map, in LOCAL time. The stored `hour`/`dow` columns
        # are UTC, and reading a Singapore cohort's routine off UTC shifts every
        # evening peak into the previous afternoon — "students work at 3pm" when
        # they actually work at 11pm. So recompute from the raw timestamp with
        # the offset applied rather than reusing the stored columns.
        # strftime('%w') is 0=Sunday; +6 %% 7 rotates to 0=Monday.
        "heatmap": _rows(
            "SELECT (CAST(strftime('%w', ts, ?) AS INTEGER) + 6) % 7 AS dow, "
            "CAST(strftime('%H', ts, ?) AS INTEGER) AS hour, "
            "COUNT(*) n FROM events WHERE ok=1 GROUP BY dow, hour",
            (TZ_OFFSET, TZ_OFFSET)),
        "tz_offset": TZ_OFFSET,
        # Divisor for the per-week average view. See _weekday_occurrences.
        **_observation_window(),
        "by_dow": _rows("SELECT dow, COUNT(*) n FROM events WHERE ok=1 "
                        "GROUP BY dow ORDER BY dow"),
        # Retention: how many students came back on N distinct days.
        "retention": _rows(
            "SELECT days, COUNT(*) students FROM ("
            "  SELECT student, COUNT(DISTINCT day) days FROM events "
            "  WHERE ok=1 AND student IS NOT NULL GROUP BY student"
            ") GROUP BY days ORDER BY days"),
        "verdicts": _rows("SELECT verdict, COUNT(*) n FROM events "
                          "WHERE tool='grade' AND ok=1 AND verdict IS NOT NULL "
                          "GROUP BY verdict"),
        "errors": _rows("SELECT error_kind, COUNT(*) n FROM events WHERE ok=0 "
                        "GROUP BY error_kind ORDER BY n DESC"),

        # --- Where understanding is weak ---
        #
        # A low mean score alone is a poor signal: it can come from two hard
        # problems, and it doesn't say what kind of weakness it is. Three things
        # together make it actionable, so they're reported on one row:
        #   students   — how widespread it is. One student failing four times is
        #                a person to help; twenty students failing once is a
        #                lecture to redo. Ranking on attempts alone conflates them.
        #   pct_wrong  — the proportion that were outright wrong, which a mean
        #                hides when scores cluster at the extremes.
        #   main_error — conceptual vs algebra decides the remedy. Reteaching
        #                fixes the first; more practice fixes the second.
        "weak_concepts": _rows(
            "SELECT topic, concept, COUNT(*) attempts, COUNT(DISTINCT student) students, "
            "ROUND(AVG(score),2) mean_score, "
            "ROUND(100.0*SUM(CASE WHEN verdict='incorrect' THEN 1 ELSE 0 END)/COUNT(*)) pct_wrong, "
            "(SELECT error_type FROM events e2 WHERE e2.concept = e1.concept "
            "  AND e2.tool='grade' AND e2.ok=1 AND e2.error_type NOT IN ('none') "
            "  GROUP BY e2.error_type ORDER BY COUNT(*) DESC LIMIT 1) main_error "
            "FROM events e1 WHERE tool='grade' AND ok=1 AND concept IS NOT NULL "
            "AND score IS NOT NULL GROUP BY topic, concept "
            "HAVING attempts >= 3 AND students >= 2 "
            "ORDER BY mean_score ASC, attempts DESC LIMIT 25"),

        # The strongest signal in the whole schema. A concept students recover
        # from after one round of feedback was a slip. A concept they attempt
        # again and still get wrong is a genuine gap in how it was taught —
        # feedback already had its chance and didn't land.
        "persistent_gaps": _rows(
            "SELECT topic, concept, COUNT(*) retries, "
            "ROUND(AVG(prior_score),2) mean_before, ROUND(AVG(score),2) mean_after, "
            "ROUND(AVG(score - prior_score),2) mean_gain "
            "FROM events WHERE prior_event_id IS NOT NULL AND score IS NOT NULL "
            "AND concept IS NOT NULL GROUP BY topic, concept "
            "HAVING retries >= 2 ORDER BY mean_gain ASC LIMIT 15"),

        # --- Student satisfaction ---
        "satisfaction": _rows(
            "SELECT SUM(CASE WHEN rating > 0 THEN 1 ELSE 0 END) helpful, "
            "SUM(CASE WHEN rating < 0 THEN 1 ELSE 0 END) not_helpful, "
            "COUNT(*) rated FROM events WHERE rating IS NOT NULL"),
        # Satisfaction is only interesting split by outcome: students who were
        # told they were wrong rating the feedback helpful is the number that
        # says the tool teaches rather than merely pleases.
        "satisfaction_by_verdict": _rows(
            "SELECT p.verdict, COUNT(*) rated, "
            "ROUND(100.0*SUM(CASE WHEN r.rating > 0 THEN 1 ELSE 0 END)/COUNT(*)) pct_helpful "
            "FROM events r JOIN events p ON p.id = r.prior_event_id "
            "WHERE r.rating IS NOT NULL AND p.verdict IS NOT NULL "
            "GROUP BY p.verdict"),

        # --- schema v2: the "did it actually help?" questions ---

        # Does feedback change the next attempt? Each row is a genuine
        # before/after pair on the same concept by the same student.
        "improvement": _rows(
            "SELECT COUNT(*) pairs, ROUND(AVG(prior_score),2) mean_before, "
            "ROUND(AVG(score),2) mean_after, ROUND(AVG(score - prior_score),2) mean_gain, "
            "SUM(CASE WHEN score > prior_score THEN 1 ELSE 0 END) improved, "
            "SUM(CASE WHEN score = prior_score THEN 1 ELSE 0 END) unchanged, "
            "SUM(CASE WHEN score < prior_score THEN 1 ELSE 0 END) worse, "
            "ROUND(AVG(minutes_since_prior)) mean_minutes_between "
            "FROM events WHERE prior_event_id IS NOT NULL AND score IS NOT NULL"),
        "improvement_by_topic": _rows(
            "SELECT topic, COUNT(*) pairs, ROUND(AVG(score - prior_score),2) mean_gain "
            "FROM events WHERE prior_event_id IS NOT NULL AND score IS NOT NULL "
            "GROUP BY topic HAVING pairs >= 2 ORDER BY mean_gain DESC"),

        # Does Socratic questioning get students there, and in how many turns?
        # Abandonment is the honest counterweight to a low median.
        "conversation_depth": _rows(
            "SELECT turns, COUNT(*) conversations FROM ("
            "  SELECT session_id, MAX(turn_index) turns FROM events "
            "  WHERE tool='chat' AND ok=1 AND session_id IS NOT NULL "
            "  GROUP BY session_id"
            ") GROUP BY turns ORDER BY turns"),

        # Short delay = answer-seeking; long delay = productive struggle.
        "solution_reveal": _rows(
            "SELECT CASE "
            "  WHEN solution_revealed_after_s IS NULL THEN 'never opened' "
            "  WHEN solution_revealed_after_s < 30 THEN 'under 30s' "
            "  WHEN solution_revealed_after_s < 120 THEN '30s-2min' "
            "  WHEN solution_revealed_after_s < 600 THEN '2-10min' "
            "  ELSE 'over 10min' END AS bucket, COUNT(*) n "
            "FROM events WHERE tool='generate' AND ok=1 GROUP BY bucket"),
    }


def export_rows(since: str | None = None) -> tuple[list[str], list[tuple]]:
    """Full event export for analysis in R/Python/SPSS."""
    conn = _connect()
    if conn is None:
        return [], []
    sql = "SELECT * FROM events"
    params: tuple = ()
    if since:
        sql += " WHERE day >= ?"
        params = (since,)
    sql += " ORDER BY id"
    with _lock:
        cur = conn.execute(sql, params)
        return [d[0] for d in cur.description], cur.fetchall()
