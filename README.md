# AI IT Helpdesk Agent

An LLM-powered helpdesk agent that reads IT support tickets, searches a knowledge base, and takes actions through tool calling. Risky actions (such as unlocking an account) pause until a human approves or rejects them.

## Screenshots

| Approval request | Final result |
|---|---|
| ![Approval card](docs/ui-approval.png) | ![Result](docs/ui-result.png) |

## Features

- **Tool calling agent loop** with tools for account lookup, account unlock, knowledge-base search and escalation
- **Knowledge-base retrieval (RAG)** over markdown help articles, so company-specific answers come only from retrieved documents
- **Open-ended help:** if no article matches, the agent gives labelled general guidance ("General guidance (not company policy)")
- **Human-in-the-loop approval:** risky actions pause the agent until a person approves or rejects through a REST endpoint or the UI
- **Audit log** of every approve or reject decision with a timestamp
- **FastAPI backend** that runs each ticket in a background thread and tracks its status
- **Ticket history in SQLite:** tickets, traces and answers are saved and survive server restarts (`GET /tickets`)
- **Streamlit dashboard** with live step-by-step agent trace and Approve / Reject buttons
- **Reliability:** retry with exponential backoff for rate limits and server errors, step limit, and recovery from empty model replies
- **Evaluation script** with 10 test tickets

## Architecture

```
Streamlit UI (ui.py)
      |  HTTP
      v
FastAPI backend (main.py)  --- background thread per ticket
      |                              |
      |                              +--> SQLite (db.py -> helpdesk.db): ticket history
      v
Agent loop (agent.py) <----> LLM API (OpenAI-compatible)
      |
      +--> Tools (tools.py): get_user_status, unlock_account, create_escalation
      +--> Knowledge base (kb.py + kb_articles/*.md)
      |
      v
Approval step: agent pauses until POST /approvals/{id}
      |
      v
audit_log.txt
```

## Tech stack

Python 3.12, FastAPI, Uvicorn, Pydantic, Streamlit, SQLite, OpenAI-compatible SDK (tested with Groq `openai/gpt-oss-120b` and Google Gemini), python-dotenv

## Project structure

```
helpdesk-agent/
├── agent.py          # agent loop, prompt, approval handling, retries
├── tools.py          # tool functions and their schemas
├── kb.py             # keyword search over help articles
├── kb_articles/      # markdown knowledge base
├── db.py             # SQLite storage for tickets
├── main.py           # FastAPI backend
├── ui.py             # Streamlit frontend
├── run_eval.py       # evaluation runner
├── eval_cases.json   # 10 test tickets
├── requirements.txt
├── .env.example
└── docs/             # screenshots
```

`helpdesk.db` and `audit_log.txt` are created automatically when the app runs. Both are listed in `.gitignore`.

## Setup

```bash
git clone https://github.com/roopali183/helpdesk-agent.git
cd helpdesk-agent
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
```

Any OpenAI-compatible provider works. Use a model that supports tool calling. Never commit your `.env` file.

## Run

Open two terminals, both with the virtual environment active.

```bash
# Terminal 1: backend
uvicorn main:app --reload

# Terminal 2: frontend
streamlit run ui.py
```

Open http://localhost:8501, submit a ticket such as `Hi, my account is locked 555`, and approve or reject the unlock request on the right.

API docs are available at http://127.0.0.1:8000/docs.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `POST /tickets` | Submit a ticket, returns a `ticket_id` |
| `GET /tickets` | Recent tickets from the database |
| `GET /tickets/{id}` | Status, trace and answer |
| `GET /approvals` | Requests waiting for a human |
| `POST /approvals/{id}` | Body `{"approve": true}` or `{"approve": false}` |
| `GET /health` | Health check |

## Evaluation

```bash
python run_eval.py            # all 10 cases
python run_eval.py 1 2 3      # selected cases
```

The 10 cases cover knowledge-base lookups, account unlock, an unknown user, a prompt-injection attempt, a security incident and general troubleshooting. A case passes when the agent calls the expected tools and avoids forbidden ones.

**Latest full run: 9 of 10 passed** (model: Groq `openai/gpt-oss-120b`). The one failure was an intermittent case where the model checked an account and then stopped without unlocking it. Errors caused by rate limits are reported separately and are not counted.

> Update this section with your own numbers after each run. The run above was made before the code-level rejection handling and demo user mode were added, so rerun the evaluation to refresh it.

## Design decisions

- **Human approval on risky tools.** The unlock tool never runs without a person's decision, and each decision is logged.
- **Human decisions are handled in code, not by the model.** In testing, the model sometimes wrote "your account has been unlocked" after a rejection. Now a rejection creates the escalation in code and returns a fixed message. A failed unlock is also reported directly.
- **Tiered answers.** Company policy comes only from retrieved articles; other problems get labelled general guidance; security and uncertain cases are escalated.
- **Guards against model quirks.** The agent recovers from empty replies and retries on rate limits.
- **Persistence with SQLite.** Every status change and trace step is written to the database. On startup, tickets that were interrupted by a restart are marked as errors, so none stay stuck in a running state.

## Limitations

- Tool data is simulated. User accounts live in memory, and in demo mode any user ID is treated as a locked mock account (`DEMO_AUTO_CREATE_USERS` in `tools.py`).
- Tickets are stored in SQLite and survive restarts. Pending approvals and the simulated user directory live in memory, so a restart cancels any ticket waiting for approval.
- Knowledge-base search is keyword-based and can return loosely related articles. Embedding-based retrieval would improve it.
- General guidance comes from the model's own knowledge and can be wrong for unusual problems.
- The evaluation set is small (10 cases) and checks tool choice, not answer quality.
- Free-tier API limits can cause temporary errors.

## Possible next steps

Docker, embedding-based retrieval, real directory integration, persistent approvals, and a larger evaluation with answer-quality checks.

## Author

Roopali Mane, MCA (AI, ML & Data Science)
