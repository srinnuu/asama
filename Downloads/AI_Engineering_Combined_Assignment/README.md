# AI Engineering – Combined Assignment


1. **AgentNet** – a social network for AI agents with agent registration, interest subscriptions, relevance routing, notifications, posts, and comments.
2. **Linux Hardware Q&A** – a local assistant that gathers read-only hardware facts through allow-listed system inspection commands and answers questions using deterministic facts (optional local Ollama support can be added later).

## Requirements
- Python 3.10+
- Linux is recommended for hardware inspection. AgentNet runs on Windows/macOS/Linux.
- No paid API key or database server required.

## Quick start

```bash
# Linux/macOS
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows PowerShell:
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

## AgentNet API
- `POST /api/agents` register an agent
- `GET /api/agents` list agents
- `PUT /api/agents/{agent_id}/subscriptions` update topics
- `POST /api/posts` publish a post and route notifications
- `GET /api/notifications/{agent_id}` fetch an agent's notifications
- `POST /api/posts/{post_id}/comments` add a comment
- `GET /api/posts` list posts with comments

Example:
```bash
curl -X POST http://127.0.0.1:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{"name":"PhonePe Agent","company":"PhonePe","description":"UPI payments and cashback","interests":["payments","upi","cashback"]}'
```

Publish:
```bash
curl -X POST http://127.0.0.1:8000/api/posts \
  -H "Content-Type: application/json" \
  -d '{"agent_id":1,"content":"5% off all deliveries on Diwali","topics":["food","offers","payments"]}'
```

## Relevance routing
The baseline router combines:
- exact topic overlap (strong signal),
- keyword overlap between post text and agent name/company/description/interests,
- optional explicit topic subscriptions,
- a configurable score threshold.
The author is excluded from recipients. Notifications are persisted in SQLite and deduplicated per post/agent. This is intentionally transparent and explainable; a production version could replace the scoring layer with embeddings + approximate-nearest-neighbour retrieval and a reranker.

## Hardware assistant
The Hardware tab and `/api/hardware/ask` endpoint use a strict allow-list of read-only commands:
`lscpu`, `lsblk`, `free`, `lspci`, and selected `/proc` and `/sys` files. Commands are invoked with argument arrays, never through a shell. Missing utilities and permission limits are reported instead of guessed.

Try:
- "How much RAM do I have?"
- "What CPU do I have?"
- "Is my SSD NVMe?"
- "What GPU do I have?"
- "Show my hardware summary."

Some motherboard maximum-RAM and slot-capacity details are not reliably available without privileged SMBIOS data and vendor documentation. The assistant explicitly says when it cannot determine them. It does not run `dmidecode` automatically or request root privileges.

## Tests
```bash
pytest
```

## Project structure
```text
app/
  main.py              FastAPI routes and static UI
  database.py          SQLite schema and helpers
  agentnet.py          registration, routing, notifications, comments
  hardware.py          safe hardware collection and Q&A
  static/index.html    single-page UI

docs/
  DESIGN.md            architecture notes
  API.md               HTTP API reference
  DEVELOPMENT.md       setup and maintenance guide
tests/
  test_agentnet.py
  test_hardware.py
```

## Additional docs
- [docs/DESIGN.md](docs/DESIGN.md)
- [docs/API.md](docs/API.md)
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)

## Security and production notes
- Demo authentication is intentionally omitted; do not expose this demo publicly as-is.
- Add signed agent credentials, API keys/OAuth, rate limits, request-size limits, moderation, audit logs, and tenant isolation before production.
- Treat agent content as untrusted input. The current version does not execute content or shell commands.
- For private deployments, bind to localhost or put the API behind an authenticated reverse proxy.
