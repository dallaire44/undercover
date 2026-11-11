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
8. The agent has three parts: `agent/api.py` (the backend), `agent/tools.py` (every tool) and `agent/harness.py` (the model, the middleware, and running the agents). Use LangChain's own mechanisms: `context_schema` with `ToolRuntime` for run state, and middleware for retries, limits and refused calls, rather than code in each tool.
9. The backend's rules know nothing of HTTP. They raise `backend.errors.NotFound` or `Refused`, and only `backend/main.py` turns them into status codes.
10. A helper lives with what it serves. Never import a helper from a module that only happens to have it.
11. Type with the domain's types, such as `State` and `RunState` in `backend/models.py`, and parameterise `list` and `dict`.
12. Agent instructions give the agent a goal, the rules it must keep and what done looks like. They are not numbered workflows: if the steps are fixed, write code instead.

`agent/tests/test_structure.py` and `backend/tests/test_structure.py` check 7, 8 and 9 on every commit.
