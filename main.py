import threading
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import db
from agent import log_audit, run_agent

app = FastAPI(title="Helpdesk Agent API")
db.init_db()

APPROVAL_TIMEOUT = 300  # seconds a human has to decide

TICKETS: dict[str, dict] = {}            # tickets of this server run (also saved to SQLite)
PENDING: dict[str, dict] = {}            # approval_id -> waiting request
EVENTS: dict[str, threading.Event] = {}  # approval_id -> wakes the agent up


class TicketRequest(BaseModel):
    ticket: str


class Decision(BaseModel):
    approve: bool


def save(ticket_id: str):
    db.save_ticket(TICKETS[ticket_id])


def make_approver(ticket_id: str):
    """Returns a function the agent calls before a risky action."""

    def approver(tool_name: str, args: dict) -> bool:
        approval_id = uuid.uuid4().hex[:8]
        event = threading.Event()
        EVENTS[approval_id] = event
        PENDING[approval_id] = {
            "id": approval_id,
            "ticket_id": ticket_id,
            "tool": tool_name,
            "args": args,
            "status": "pending",
        }
        TICKETS[ticket_id]["status"] = "waiting_approval"
        save(ticket_id)

        decided = event.wait(timeout=APPROVAL_TIMEOUT)  # agent pauses here

        if not decided:
            PENDING[approval_id]["status"] = "expired"
            log_audit(tool_name, args, "EXPIRED")
            TICKETS[ticket_id]["status"] = "running"
            save(ticket_id)
            return False

        approved = PENDING[approval_id]["status"] == "approved"
        log_audit(tool_name, args, "APPROVED" if approved else "REJECTED")
        TICKETS[ticket_id]["status"] = "running"
        save(ticket_id)
        return approved

    return approver


def worker(ticket_id: str, text: str):
    """Runs the agent in the background."""

    def on_step(step):
        TICKETS[ticket_id]["trace"].append(step)
        save(ticket_id)

    try:
        answer = run_agent(text, approver=make_approver(ticket_id), on_step=on_step)
        TICKETS[ticket_id]["answer"] = answer
        TICKETS[ticket_id]["status"] = "done"
    except Exception as e:
        TICKETS[ticket_id]["error"] = str(e)
        TICKETS[ticket_id]["status"] = "error"
    save(ticket_id)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tickets")
def create_ticket(req: TicketRequest):
    ticket_id = uuid.uuid4().hex[:8]
    TICKETS[ticket_id] = {
        "ticket_id": ticket_id,
        "ticket": req.ticket,
        "status": "running",
        "answer": None,
        "error": None,
        "trace": [],
    }
    save(ticket_id)
    threading.Thread(target=worker, args=(ticket_id, req.ticket), daemon=True).start()
    return {"ticket_id": ticket_id, "status": "running"}


@app.get("/tickets")
def ticket_history(limit: int = 20):
    """Recent tickets from the database (survives restarts)."""
    return db.list_tickets(limit)


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    ticket = TICKETS.get(ticket_id) or db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.get("/approvals")
def list_approvals():
    return [p for p in PENDING.values() if p["status"] == "pending"]


@app.post("/approvals/{approval_id}")
def decide(approval_id: str, decision: Decision):
    item = PENDING.get(approval_id)
    if not item:
        raise HTTPException(status_code=404, detail="Approval not found")
    if item["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Already {item['status']}")
    item["status"] = "approved" if decision.approve else "rejected"
    EVENTS[approval_id].set()  # wake the agent up
    return item