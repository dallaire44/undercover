# Python design issues

A review of `backend/` and `agent/` against the python-design guidance. Tests,
`monitor.py` and the course folders are out of scope. Ranked by value; none is a bug
today.

The python-design skill judges whether structure (interfaces, patterns, layers) is
warranted and light. The code passes it; see the last section. Each finding's Basis
line says where it comes from: the skill, `HUMAN_REVIEW_HARNESS.md` (which sets the
module layout this project expects), or a general code review.

## Status

Fixed on 2026-11-11:

- 2, 3, 4, 10 and the agent's part of 12: `9814667`, the agent rebuilt as `api.py`,
  `tools.py` and `harness.py`.
- 1 and 5: `2fe0705`, `backend/errors.py` and `db.now()`.
- 6, 8, 9, 11 and the backend's part of 12, and 7 in part: `485b7e2`.
- The instructions point in `HUMAN_REVIEW_HARNESS.md`: `275cc47`.

Left as they are: `runs.claims_to_work` still filters the whole queue in Python (fine at
25 claims), and a stopped run still records its run id as the thread of the step it
adds, now passed explicitly.

## Medium

### 1. Domain modules raise FastAPI's HTTPException
Basis: skill, "separate domain logic from I/O", applied to the web framework. The fix
follows the skill's Repository example (`PositionNotFound(LookupError)`).

`records.py`, `rules.py`, `runs.py` and `documents.py` raise `fastapi.HTTPException`
(404) and `rules.conflict()` builds one (409). The rules then depend on the web
framework, and code that runs outside a request uses them anyway:
`runner.run_queue` calls `runs.row` and `runs.stop` from a background task.
Fix: two plain exceptions, `NotFound(LookupError)` and `Refused(Exception)`, raised by
the domain modules, and two `@app.exception_handler`s in `main.py` that turn them into
404 and 409.

### 2. No single backend API module
Basis: skill, "a thin wrapper around a third-party client", and
`HUMAN_REVIEW_HARNESS.md`. The duplication is general review.

- The base URL is in one place (`agent/api.py`), but 22 endpoint paths are spread over
  `queue.py` (9), `tools.py` (8), `cli.py` (3) and `claim.py` (2).
- There are two ways to call the backend: `tools.call`, which returns refusals as
  text, and raw `api.backend()` clients in `claim.py`, `queue.py` and `cli.py`.
  `queue.py` imports `call` from `tools.py`.
- Turning a 4xx into its `detail` is written three times: `tools.call`, `cli.start`,
  `queue.work_claim`. Posting a step is written twice: `claim.run` and `queue.note`.

Fix: `agent/api.py` has one function per backend operation, the base URL and the
refusal handling. Nothing else builds a path or a client.

### 3. The tools are in two modules
Basis: `HUMAN_REVIEW_HARNESS.md`.

The claim agent's tools are in `tools.py`, and the queue agent's four
(`list_claims_to_work`, `write_todos`, `work_claim`, `finish_run`) are in `queue.py`.
Fix: all tools in `tools.py`, each calling `api`. `work_claim` needs the claim agent,
so import the harness module (not names from it) to avoid an import cycle.

### 4. No single harness module
Basis: `HUMAN_REVIEW_HARNESS.md`.

Building and running the agents is spread over `model.py` (the model and middleware),
`claim.py` (the claim agent and streaming its steps) and `queue.py` (the queue agent
and `work_claim`), mixed with UnderCover wording such as `outcome()`, `line()` and
`VERDICTS`. Fix: `harness.py` builds and runs both agents with their model and
middleware; the domain wording stays with the tools that produce it.

### 5. rules.py doubles as a utilities module
Basis: general review, module cohesion.

`rules.now()` and `rules.conflict()` are used by `steps.py`, `runs.py` and `runner.py`,
so `steps` imports `rules` just for the clock. Fix: with issue 1, `conflict` goes away;
move `now` next to the database code in `db.py`.

## Low

### 6. Claim and run states are typed as plain str
Basis: general review, typing.

`models.py` defines `State` and `RunState`, but `rules.set_status(state: str)` and
`runs.close(state: str)` take any string, and `runs.claim_ids(state="%")` uses a SQL
`LIKE` wildcard as "any state". Fix: annotate with the Literals, and make the filter
`state: State | None = None`.

### 7. One claim is found by loading them all
Basis: general review, efficiency.

`records.summary` builds every claim's summary, with every customer, to return one, and
`take_claim` and `return_claim` call it. `runs.claims_to_work` does the same.
`records.get_claim` queries the `claims` table three times (doc, attempts, status).
Fine at the pilot's size. Fix when it matters: one query for one claim's row, shared by
`status`, `summary` and `get_claim`.

### 8. Table and key passed together
Basis: general review, tidiness.

`records.document(conn, "handlers", "handler_id", value)` repeats the key that
`db.DOCUMENTS` already maps from the table. Fix: `document(conn, table, value)`, with
the key looked up in `db.DOCUMENTS`.

### 9. An API request model used as an internal argument
Basis: general review, close to the skill's "pass the specific values each function
needs".

`runs.stop` builds `ReturnRequest(thread_id=run_id, ...)` to call `return_claim`, so a
run id is stored as a thread id. Fix: `return_claim(conn, claim_id, thread_id, reason)`
takes plain values, and `main.py` unpacks the request.

### 10. Loading .env at import, with override
Basis: general review, side effect at import.

`agent/model.py` calls `load_dotenv(override=True)` at import. The backend imports it
through `runner -> agent.queue`, so a `.env` value would beat environment variables set
by Playwright (`UNDERCOVER_DB`, `UNDERCOVER_AGENT`) or the shell. Today `.env` holds only
`OPENROUTER_API_KEY`, so this is latent. Fix: drop `override=True`, or load `.env` in
the entry points.

### 11. Data files read on every call
Basis: general review, efficiency.

`rules.approval_limit()` reads `company.json` each call (twice in `pay_claim`), and
`records.get_policy` reads `plans.json` each call, while `documents.sections` is
cached. Fix: `@cache` on `db.load`.

### 12. Bare list and dict annotations
Basis: general review, typing.

`model.claim_middleware() -> list`, `queue_middleware() -> list`,
`tools.call(body: dict | None, params: dict | None)`, `queue.outcome(record: dict)`,
`queue.line(found: dict)`, `records.document(...) -> dict`. Fix: parameterise them,
such as `list[AgentMiddleware]` and `dict[str, Any]`.

## Checked and left as they are
- No Protocols: each part has one real implementation, and tests use the real backend
  through `TestClient`.
- `llm: BaseChatModel | None` on `claim.run` and `queue.run_queue`: a parameter is the
  lightest test seam.
- `api.backend()` makes a client per call: simple, and tests patch the one function.
- `queue.TodoItem` repeats `backend.models.Todo`: it keeps the agent apart from the
  backend's package at the API boundary.
- `runner.py` imports `agent.queue`: it is the one place the two are wired together.
- Already met from `HUMAN_REVIEW_HARNESS.md`: the base URL in one place, no
  `agent/main.py`, and `context_schema` with `ToolRuntime`. Its point on prescriptive
  instructions is not Python and is not reviewed here.
