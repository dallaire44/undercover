# Code standards

1. Keep it simple, do not overcomplicate.
2. Comments only when necessary.
3. Be concise: a short README and no emojis.
4. IMPORTANT: avoid overly defensive code. Handle exceptions only when necessary.
5. Use uv: ALWAYS `uv run`, NEVER `python3`.
6. TypeScript: strict mode, never `any`.

## Structure

Code must be fit for a pull request: one place for each concern, and no shortcuts.

7. One API module per client. The agent reaches the backend only through `agent/api.py`, and the dashboard only through `dashboard/src/api.ts`: one function per operation, with the base URL in one place. No other module builds a URL or opens a client.
8. The agent has five parts: `agent/api.py` (the backend), `agent/tools.py` (every tool), `agent/harness.py` (the model, the claim agent's graph, and running it), `agent/dispatcher.py` (working a run's claims, N at once, through `harness.work_claim` alone) and `agent/service.py` (its entry point). Use LangChain's and LangGraph's own mechanisms: the claim graph's nodes for its retries, limits and refused calls, rather than code in each tool, and the dispatcher's `Send`, `max_concurrency`, `RetryPolicy` and `error_handler` rather than threads and loops of your own.
9. The backend's rules know nothing of HTTP. They raise `backend.errors.NotFound` or `Refused`, and only `backend/main.py` turns them into status codes.
10. A helper lives with what it serves. Never import a helper from a module that only happens to have it.
11. Type with the domain's types, such as `State` and `RunState` in `backend/models.py`, and parameterise `list` and `dict`.
12. Agent instructions give the agent a goal, the rules it must keep and what done looks like. They are not numbered workflows: if the steps are fixed, write code instead.

`agent/tests/test_structure.py` and `backend/tests/test_structure.py` check 7, 8 and 9 on every commit: that the dispatcher touches the claim agent only through `harness.work_claim` and imports no tools, that the backend reaches the agent only through `backend/agent_service.py`, which alone knows its address and routes, that only `backend/usage.py` touches the model calls and work times, and that only `backend/scores.py` reads the answer key, which the agent never asks for.
