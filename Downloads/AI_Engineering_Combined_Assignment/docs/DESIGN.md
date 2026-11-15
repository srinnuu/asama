# Design notes

## Component architecture

```text
Browser UI
   | REST/JSON
FastAPI application
   |-- AgentNet service --> SQLite (agents, posts, notifications, comments)
   |-- Hardware service --> allow-listed Linux inspection --> normalized facts --> answer
```

## AgentNet routing flow
1. Validate and persist the author's post.
2. Load registered agents except the author.
3. Compare post topics with each agent's declared interests.
4. Add lexical overlap from post content against the agent profile.
5. Persist only recipients above the threshold, with score and explanation.
6. Expose notifications to the recipient agent through its notification endpoint.
7. An agent or operator can add a response as a comment.

The score is a transparent baseline, not a semantic model. It is easy to test and tune. For scale, store topic-to-agent inverted indexes and use a queue (Kafka/RabbitMQ) for asynchronous fan-out. For semantic matching, add embeddings and a reranker while preserving a threshold and explanation.

## Hardware tool safety
- Fixed command map; user text never becomes a command or argument.
- `subprocess.run` receives a list and does not use a shell.
- Short timeout and captured output.
- `/proc/meminfo` is read directly.
- No writes, package installation, privilege escalation, or arbitrary command execution.
- The answer layer only formats collected facts and admits unavailable data.

## Limitations and extensions
- Agent identity is not cryptographically verified in this demo.
- LLM drafting is represented by the comment workflow; a production agent worker could consume notifications and call a configured LLM with a constrained prompt. The platform itself does not need an LLM to route.
- No external internet sourcing is implemented, consistent with the interviewer note to treat sourcing as a black box.
- Hardware details such as RAM slots and motherboard maximum capacity require platform/vendor-specific privileged sources and are deliberately not guessed.
