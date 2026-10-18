import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DB_PATH = Path(__file__).resolve().parents[2] / "outputs" / "triage_sessions.db"


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Open a connection, commit on success, and always close it.

    sqlite3's own context manager only commits; it never closes, which leaked
    a connection per request.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS triage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                triage_level TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_triage_logs_session ON triage_logs (session_id)")
        # One row per session once staff act on it; no row means still waiting.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_status (
                session_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT NOT NULL DEFAULT ''
            )
            """
        )


def insert_triage_log(session_id: str, triage_level: str, payload: dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO triage_logs (session_id, triage_level, payload_json)
            VALUES (?, ?, ?)
            """,
            (session_id, triage_level, json.dumps(payload)),
        )


def get_latest_triage_log(session_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT t.session_id, t.triage_level, t.created_at, t.payload_json,
                   (SELECT MIN(created_at) FROM triage_logs WHERE session_id = t.session_id) AS arrived_at,
                   COALESCE(s.status, 'waiting') AS status, s.updated_at AS completed_at, s.updated_by AS completed_by
            FROM triage_logs t
            LEFT JOIN session_status s ON s.session_id = t.session_id
            WHERE t.session_id = ?
            ORDER BY t.id DESC
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()

    if row is None:
        return None

    payload = json.loads(row["payload_json"])
    return {
        **_status_fields(row),
        "session_id": row["session_id"],
        "triage_level": row["triage_level"],
        "created_at": row["created_at"],
        "arrived_at": row["arrived_at"],
        "request_payload": payload.get("request", {}),
        "response_payload": payload.get("response", {}),
    }


def set_session_status(session_id: str, status: str, updated_by: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO session_status (session_id, status, updated_at, updated_by)
            VALUES (?, ?, strftime('%Y-%m-%d %H:%M:%f', 'now'), ?)
            ON CONFLICT(session_id) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at,
                updated_by = excluded.updated_by
            """,
            (session_id, status, updated_by),
        )


def _status_fields(row: sqlite3.Row) -> dict[str, Any]:
    done = row["status"] == "done"
    return {
        "status": row["status"],
        "completed_at": row["completed_at"] if done else None,
        "completed_by": row["completed_by"] if done else None,
    }


def list_recent_triage_logs(limit: int = 50, status: str = "waiting") -> list[dict[str, Any]]:
    """One entry per patient session (its latest triage), filtered by status.

    waiting / all: most urgent first, then whoever has waited longest.
    done: most recently seen first.
    """
    with get_conn() as conn:
        rows = conn.execute(
            """
            WITH sessions AS (
                SELECT session_id, MAX(id) AS latest_id, MIN(created_at) AS arrived_at
                FROM triage_logs
                GROUP BY session_id
            )
            SELECT t.id, t.session_id, t.triage_level, t.created_at, t.payload_json, sessions.arrived_at,
                   COALESCE(s.status, 'waiting') AS status, s.updated_at AS completed_at, s.updated_by AS completed_by
            FROM sessions
            JOIN triage_logs t ON t.id = sessions.latest_id
            LEFT JOIN session_status s ON s.session_id = t.session_id
            WHERE :status = 'all' OR COALESCE(s.status, 'waiting') = :status
            ORDER BY
                CASE WHEN :status = 'done' THEN s.updated_at END DESC,
                CASE t.triage_level
                    WHEN 'RED' THEN 0
                    WHEN 'ORANGE' THEN 1
                    ELSE 2
                END,
                sessions.arrived_at ASC,
                t.id ASC
            LIMIT :limit
            """,
            {"status": status, "limit": limit},
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        request = json.loads(row["payload_json"]).get("request", {})
        items.append(
            {
                **_status_fields(row),
                "session_id": row["session_id"],
                "triage_level": row["triage_level"],
                "created_at": row["created_at"],
                "arrived_at": row["arrived_at"],
                "patient_name": request.get("patient_name", ""),
                "age_group": request.get("age_group"),
                "sex": request.get("sex"),
                "entered_by": request.get("entered_by"),
                "chief_complaint_text": request.get("chief_complaint_text", ""),
            }
        )
    return items
