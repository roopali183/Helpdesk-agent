import json
import sqlite3

DB_FILE = "helpdesk.db"


def _conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the table, and close tickets that were interrupted by a restart."""
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS tickets (
                ticket_id  TEXT PRIMARY KEY,
                ticket     TEXT,
                status     TEXT,
                answer     TEXT,
                error      TEXT,
                trace      TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        c.execute(
            "UPDATE tickets SET status='error', error='Server restarted before this ticket finished' "
            "WHERE status IN ('running', 'waiting_approval')"
        )


def save_ticket(t: dict):
    """Insert a ticket, or update it if it already exists."""
    with _conn() as c:
        c.execute(
            """INSERT INTO tickets (ticket_id, ticket, status, answer, error, trace)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(ticket_id) DO UPDATE SET
                   status=excluded.status,
                   answer=excluded.answer,
                   error=excluded.error,
                   trace=excluded.trace""",
            (
                t["ticket_id"], t["ticket"], t["status"], t["answer"],
                t["error"], json.dumps(t["trace"], default=str),
            ),
        )


def _to_dict(row):
    d = dict(row)
    d["trace"] = json.loads(d["trace"] or "[]")
    return d


def get_ticket(ticket_id: str):
    with _conn() as c:
        row = c.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
    return _to_dict(row) if row else None


def list_tickets(limit: int = 20):
    with _conn() as c:
        rows = c.execute(
            "SELECT ticket_id, ticket, status, created_at FROM tickets "
            "ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    save_ticket({"ticket_id": "test1", "ticket": "hello", "status": "done",
                 "answer": "hi", "error": None, "trace": [{"step": 1, "tool": "x"}]})
    print(get_ticket("test1"))
    with _conn() as c:
        c.execute("DELETE FROM tickets WHERE ticket_id='test1'")
    print("OK, test ticket removed")