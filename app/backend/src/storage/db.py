import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[2] / "outputs" / "triage_sessions.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
            SELECT session_id, triage_level, created_at, payload_json
            FROM triage_logs
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()

    if row is None:
        return None

    payload = json.loads(row["payload_json"])
    return {
        "session_id": row["session_id"],
        "triage_level": row["triage_level"],
        "created_at": row["created_at"],
        "request_payload": payload.get("request", {}),
        "response_payload": payload.get("response", {}),
    }


def list_recent_triage_logs(limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT session_id, triage_level, created_at, payload_json
            FROM triage_logs
            ORDER BY
                CASE triage_level
                    WHEN 'RED' THEN 0
                    WHEN 'ORANGE' THEN 1
                    ELSE 2
                END,
                created_at DESC,
                id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        request = payload.get("request", {})
        items.append(
            {
                "session_id": row["session_id"],
                "triage_level": row["triage_level"],
                "created_at": row["created_at"],
                "patient_name": request.get("patient_name", ""),
                "age_group": request.get("age_group"),
                "sex": request.get("sex"),
                "chief_complaint_text": request.get("chief_complaint_text", ""),
            }
        )
    return items
