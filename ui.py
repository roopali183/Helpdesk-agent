import os
import time

import requests
import streamlit as st

# Default works on your own computer. Docker sets API_URL to the backend container.
API = os.environ.get("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Helpdesk Agent", page_icon="🛠️", layout="wide")
st.title("🛠️ IT Helpdesk AI Agent")

if "ticket_id" not in st.session_state:
    st.session_state.ticket_id = None


def api_get(path):
    try:
        return requests.get(f"{API}{path}", timeout=10).json()
    except Exception as e:
        st.error(f"Cannot reach the API. Is the backend running? ({e})")
        return None


def api_post(path, body):
    try:
        return requests.post(f"{API}{path}", json=body, timeout=10).json()
    except Exception as e:
        st.error(f"Cannot reach the API. Is the backend running? ({e})")
        return None


left, right = st.columns([1, 1])

# ---------- Left: submit and watch a ticket ----------
with left:
    st.subheader("1. Submit a ticket")
    text = st.text_area(
        "Describe the problem",
        value="Hi, my account is locked. My user id is u101. Please help.",
        height=100,
    )
    if st.button("Submit ticket", type="primary"):
        res = api_post("/tickets", {"ticket": text})
        if res and "ticket_id" in res:
            st.session_state.ticket_id = res["ticket_id"]

    tid = st.session_state.ticket_id
    if tid:
        ticket = api_get(f"/tickets/{tid}")
        if ticket and "status" in ticket:
            st.subheader(f"2. Ticket {tid}")
            status = ticket["status"]
            icon = {"running": "⏳", "waiting_approval": "🛑", "done": "✅", "error": "❌"}
            st.markdown(f"**Status:** {icon.get(status, '')} `{status}`")

            for s in ticket["trace"]:
                with st.expander(f"Step {s['step']}: {s['tool']}", expanded=False):
                    st.json({"args": s["args"], "result": s["result"]})

            if ticket["answer"]:
                st.success(ticket["answer"])
            if ticket["error"]:
                st.error(ticket["error"])
        elif ticket:
            st.warning("This ticket was not found. Submit a new one.")

# ---------- Right: approvals ----------
with right:
    st.subheader("Pending approvals")
    approvals = api_get("/approvals") or []
    if not approvals:
        st.info("Nothing waiting for approval.")
    for a in approvals:
        with st.container(border=True):
            st.markdown(f"**{a['tool']}**  \nArgs: `{a['args']}`  \nTicket: `{a['ticket_id']}`")
            c1, c2 = st.columns(2)
            if c1.button("✅ Approve", key=f"yes_{a['id']}"):
                api_post(f"/approvals/{a['id']}", {"approve": True})
                st.rerun()
            if c2.button("❌ Reject", key=f"no_{a['id']}"):
                api_post(f"/approvals/{a['id']}", {"approve": False})
                st.rerun()

# ---------- Auto refresh while the agent is working ----------
tid = st.session_state.ticket_id
if tid:
    current = api_get(f"/tickets/{tid}")
    if current and current.get("status") in ("running", "waiting_approval"):
        time.sleep(2)
        st.rerun()