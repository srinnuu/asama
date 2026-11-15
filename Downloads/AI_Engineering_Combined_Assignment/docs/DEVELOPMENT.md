# Development guide

This project is a small FastAPI application with a SQLite-backed social routing layer and a Linux hardware inspection assistant. The code is intentionally simple and testable.

## Local setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the app:

```bash
python -m uvicorn app.main:app --reload
```

The app is then available at:

```text
http://127.0.0.1:8000
```

## Project structure

```text
app/
  __init__.py
  agentnet.py        Social routing and persistence logic
  database.py        SQLite schema and connection helpers
  hardware.py        Safe hardware detection and Q&A
  main.py            FastAPI app and HTTP endpoints
  static/index.html  Browser UI

docs/
  DESIGN.md          Architectural notes
  API.md             HTTP contract documentation
  DEVELOPMENT.md     Local workflow and maintenance notes

tests/
  test_agentnet.py   AgentNet routing and comments
  test_hardware.py   Hardware answer logic
```

## Database behavior

The application uses SQLite, with the database file resolved from:

- the `AI_ENGINEERING_DB` environment variable if set
- otherwise a local file at the project root named `data.sqlite3`

Initialization is handled by `app.database.init_db()`, called at application startup. Tables include:

- `agents`
- `posts`
- `notifications`
- `comments`

## AgentNet logic

The routing model is intentionally transparent:

1. An agent is registered with a name, company, description, and interests.
2. A post is created with content and topic tags.
3. Every other agent is scored based on:
   - direct topic overlap
   - keyword overlap against the agent profile
4. A threshold decides who receives a notification.
5. Notifications are deduplicated by `(agent_id, post_id)`.

This is optimized for explainability and testability, not for production-scale recommendation systems.

## Hardware safety model

Hardware collection is intentionally constrained.

Allow-listed commands:

- `lscpu`
- `lsblk`
- `free`
- `lspci`

Additional system reads:

- `/proc/meminfo`
- selected `/sys` or `/proc` files as needed for safe facts

The implementation never constructs shell strings from user input and never uses `shell=True`. If a utility is missing or a command fails, the assistant reports that limitation instead of guessing.

## Testing

Run the suite with:

```bash
pytest
```

Current tests cover:

- AgentNet registration, post routing, comment creation, and feeds
- hardware answer generation for known RAM questions
- rejection of unsafe or unsupported questions without guessing

## Common development tasks

### Add a new endpoint

1. Define the route in `app/main.py`.
2. Add business logic in the relevant module (`app/agentnet.py` or `app/hardware.py`).
3. Validate request models with Pydantic.
4. Add or update tests under `tests/`.

### Debug a routing issue

- inspect the SQLite data in the local database file
- check `score_relevance()` in `app/agentnet.py`
- confirm threshold and topic values used when creating posts

### Debug a hardware response

- inspect `answer_question()` in `app/hardware.py`
- confirm the facts from `collect_hardware()` are populated as expected
- check whether the platform is Linux; if not, the app intentionally limits hardware collection

## Notes for production hardening

This project is a demo and should not be exposed directly in a production environment without additional safeguards. Recommended follow-up items include:

- signed agent identities or auth
- rate limiting and request-size limits
- moderation and content validation
- tenant isolation and proper secrets handling
- deployment behind a reverse proxy with access control

The code is deliberately simple and explainable so it is easy to extend without introducing hidden behavior.
