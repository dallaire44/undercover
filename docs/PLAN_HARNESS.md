# Plan: the agent's harness

The brief is `docs/HARNESS.md`. This plan builds on the pilot as `docs/STATUS.md` describes it, in six phases. Each phase ends green on the pre-commit checks and is committed. Tests never call a model: agent tests use the existing `StubModel` (`agent/tests/conftest.py`), and runner tests replace the agent with a plain function.

## The shape of the build

Today the backend organizes the work. `runner.run_queue` loops over the waiting claims and calls the agent once per claim, and the agent reads the whole policy wording every time. After this build, two agents built with LangChain's `create_agent` do the work, and the backend keeps the records and enforces the rules.

- **The queue agent** (`agent/queue.py`) works a **run**. It lists the claims it may work, writes a to-do list, hands each claim to a claim agent with its `work_claim` tool, keeps the list up to date, checks for missed claims and finishes the run with a summary.
- **The claim agent** (`agent/claim.py`, the pilot's `agent/main.py` renamed) works one claim from a fresh start. It runs on a new thread with nothing from earlier claims in its context. It finds the sections of the wording and the manual it needs with three lookup tools.
- **`work_claim`** is the bridge between the two. It is plain code, not a model. It takes the claim into the run, runs the claim agent, and if the attempt fails it returns the claim to the backend. It always answers the queue agent in one line, such as `CLM-1004: approved, paid $420.00` or `CLM-1009: failed (timed out), back in the queue, attempt 1 of 2`.

Why this split: the brief asks the agent to organize its own work, so the order, the to-do list and the summary come from the queue agent. The things that must hold even when a model misbehaves are enforced by the backend, so a test can prove them without a model:

- the cap on a run
- no claim decided or paid twice (the pilot's 409s already do this)
- two failures and a claim is left for a handler
- no finishing a run while a claim within its cap is still waiting

We build all of this into our own agent with LangChain's built-in middleware and our own tools, and add no other agent framework, as the brief asks.

### Choices for you to review

1. **A new claim state, `needs_handler`** ("Needs a handler"), for a claim that failed twice. It is not a decision, so the Decision and Payout columns stay empty. It uses Raspberry, the brand's alert color, and reddish purple `#CC79A7` in color-blind mode, the same pair as "Payment on hold", since both mean a handler must act.
2. **What counts as a failure.** An attempt fails if the claim agent raises an error, or if it ends with the claim still `in_progress`. That covers no decision, and also an approval of $1,000 or less that was never paid. Either way the claim goes back to `waiting` with its attempt count raised by one, and on the second failure to `needs_handler`. A retry of an approved but unpaid claim finds the decision already recorded. The instructions tell the agent to pay it and not decide again, and the backend refuses a second decision anyway. A claim that is `decided` or `awaiting_sign_off` has not failed, whatever happened after.
3. **The cap is enforced by the backend.** A run has a `cap`, and `take_claim` refuses a new claim once the run holds `cap` claims. A claim that failed and went back to the queue stays in its run, so the retry does not use up the cap.
4. **The missed-claims check is enforced too.** The queue agent calls `list_claims_to_work` before it finishes, as its instructions say, and `finish_run` refuses with 409, naming the claims, while any remain.
5. **Every agent start is a run.** "Work the queue" starts a run with a cap. "Run the agent" on one claim starts a run with a cap of 1 that calls `work_claim` directly, with no queue agent and no to-do list, so it costs one claim agent. Only one run at a time: starting another while one is running is refused with 409.
6. **Retries and limits come from middleware.** `ModelRetryMiddleware` retries a failed model call with backoff (timeouts and provider errors). `ModelCallLimitMiddleware` stops a claim agent that loops past 30 model calls. When the retries run out or the limit is hit, the attempt raises an error, and `work_claim` turns that into a failed attempt.
7. **What the agent read is a step of its own.** A `read_section` result is recorded as a step of kind `read`, whose first line names the document and section, such as `Claims manual, 9. Repeat claims`. The claim page lists those as "Sections read", and the timeline shows them too.
8. **The to-do list is the queue agent's own tool**, `write_todos`, which replaces the whole list each time. LangChain's `TodoListMiddleware` keeps its list inside the agent's state, where the dashboard cannot see it, and has no "left for a handler" status. So the list is stored in the backend.
9. **The e2e backend never starts an agent.** Its server runs with `UNDERCOVER_AGENT=off`, so "Work the queue" in an e2e test creates the run and nothing works it. The test then acts as the agent through the API, as the pilot's e2e tests do.
10. **The dashboard's cap starts at 5**, so a trial is cheap by default. A handler can raise it, up to the number of waiting claims.

## The API after this build

New or changed operations. Each has an `operation_id`, a one-line docstring and no optional inputs, and `backend/tests/test_openapi.py` keeps checking all of them.

| Operation | Route | What it does |
|---|---|---|
| `list_sections` | `GET /api/documents` | The table of contents of the policy wording and the claims manual |
| `search_documents` | `GET /api/documents/search?query=` | The sections whose text matches the words of the query, best first, each with a matching line |
| `read_section` | `GET /api/documents/{document}/sections/{number}` | One section, with a first line naming it. `document` is `policy_wording` or `claims_manual` |
| `get_instructions` | `GET /api/instructions/{agent}` | The instructions for `queue` or `claim` (changed from one text) |
| `start_run` | `POST /api/runs` `{cap}` | Start a queue run in the background. 409 if a run is running |
| `start_agent` | `POST /api/claims/{id}/agent` | Start a run with a cap of 1 on one waiting claim (changed) |
| `get_latest_run` | `GET /api/runs/latest` | The latest run with its to-do list, or `null` |
| `get_run` | `GET /api/runs/{run_id}` | One run with its claims, to-do list and summary |
| `list_claims_to_work` | `GET /api/runs/{run_id}/claims-to-work` | The waiting claims this run may still work: its own returned claims, and any waiting claim while under its cap |
| `take_claim` | `POST /api/runs/{run_id}/claims/{claim_id}` | Waiting to `in_progress`, in this run. 409 past the cap, or if the claim is not waiting |
| `return_claim` | `POST /api/claims/{id}/return` `{reason}` | After a failed attempt: attempts plus one, then `waiting`, or `needs_handler` on the second failure. Records the reason as a step. 409 unless `in_progress` |
| `write_todos` | `PUT /api/runs/{run_id}/todos` `{todos}` | Replace the run's to-do list. Each item is `{content, status}`, status `to_do`, `in_progress`, `done` or `left_for_handler` |
| `finish_run` | `POST /api/runs/{run_id}/finish` `{summary}` | Finish with a summary. 409 if claims are still to work or one is in progress |

Removed: `work_queue`, replaced by `start_run`, and `get_policy_wording`, since the agent now reads sections, never the whole document.

New tables: `runs` (id, cap, status `running`/`finished`/`stopped`, summary, start and finish times) and `todos` (run, position, content, status). Two new columns on `claims`: `attempts` and `run_id`. The schema changes, so the dev database must be rebuilt with `npm run reset` after Phase 2.

---

## Phase 1: Look up the manual and the wording, and the new model

The claim agent stops reading the whole wording and looks up sections instead. This phase also brings in the claims manual, and the model changes to DeepSeek V4.1 Flash.

- `backend/documents.py`: split `data/policy_wording.md` and `data/claims_manual.md` on their `## ` headings into numbered sections. Add a table of contents, a word search (a section's score is how many of the query's words it contains, ignoring case, with sections that match no words left out) and reading one section.
- The three document operations above; remove `get_policy_wording`.
- `agent/tools.py`: swap `get_policy_wording` for `list_sections`, `search_documents` and `read_section`.
- The agent turns a `read_section` result into a step of kind `read`. `StepRequest.kind` accepts `read`.
- `agent/model.py`: `model()` uses `deepseek/deepseek-v4.1-flash` with low reasoning effort by default, or `MODEL_NAME` if set.
- The claim agent gets `ModelRetryMiddleware` (2 retries, raising when they run out) and `ModelCallLimitMiddleware` (30 model calls, raising past them).
- `backend/instructions/claim.md`: the claim agent's instructions, rewritten from the policy wording and the manual (never from `data/evals/`). They cover:
  - the order of work in manual section 4
  - which sections to look up for what: the benefit's section of the wording, manual 5 for required documents, 6 for the payout, 7 for interpretation notes, 8 when the story and documents disagree, 9 for repeat claims and 10 for meals without receipts
  - the wording comes first (manual section 1)
  - what to do on a retry: don't decide again, pay an approved claim that is unpaid
  - finish with one line

  `get_instructions` serves it at `/api/instructions/claim`, and the old `backend/instructions.md` goes.

Success criteria:

- [x] `uv run pytest backend/tests/test_documents.py` passes. It checks that:
  - the contents list all 12 wording sections and all 14 manual sections
  - `read_section("claims_manual", "9")` starts `Claims manual, 9. Repeat claims` and holds that section's text and no other's
  - an unknown document or section is 404
  - searching "wild animals" ranks manual section 7 first, and searching "meals receipts" includes manual section 10
- [x] `curl "http://localhost:8000/api/documents/search?query=third%20claim"` with the backend up returns manual section 9 among the results, and `curl http://localhost:8000/api/policy-wording` returns 404.
- [x] An agent test on a stub model calls `search_documents`, then `read_section` twice, then decides. The claim's steps include two of kind `read`, whose first lines name the sections.
- [x] An agent test: a stub model that raises a provider error once, then works the claim, still decides it, so `ModelRetryMiddleware` retried. A stub that never stops calling tools raises after 30 model calls.
- [x] `test_model_name`: the default is `deepseek/deepseek-v4.1-flash` with `reasoning_effort="low"`, and `MODEL_NAME=openrouter/free` overrides it.
- [x] `grep -ri "evals" backend/instructions/` finds nothing, and the instructions name no handler decision.
- [x] `test_openapi.py` passes with the new operations.
- [x] The pre-commit checks pass and the phase is committed.

## Phase 2: Runs, the cap, the to-do list and failure handling in the backend

The records and rules that let one run work the queue safely, with no agent yet.

- `backend/db.py`: the `runs` and `todos` tables, and `attempts` and `run_id` on `claims`.
- `backend/runs.py`: `start`, `get`, `latest`, `claims_to_work`, `take_claim`, `return_claim`, `write_todos`, `finish` and `stop`, each with the rules above.
- `backend/models.py`: `RunRequest`, `Run`, `Todo`, `TodoList`, `FinishRequest` and `ReturnRequest`. `State` gains `needs_handler`.
- The operations `get_latest_run`, `get_run`, `list_claims_to_work`, `take_claim`, `return_claim`, `write_todos` and `finish_run`. `start_run` and `start_agent` come in Phase 3, with the agent.
- Recovery on startup: a run still `running` becomes `stopped` with "The backend restarted during the run", and each claim left `in_progress` is returned as a failed attempt. A restart never leaves a claim stuck in progress.

Success criteria:

- [x] `uv run pytest backend/tests/test_runs.py` passes, with a test for each rule:
  - [x] **The cap:** a run with cap 2 takes CLM-1001 and CLM-1002, and taking CLM-1003 is 409 "The run's cap of 2 claims is reached". `list_claims_to_work` is then empty, and CLM-1003 stays `waiting`.
  - [x] **Back in the queue:** returning an `in_progress` claim makes it `waiting` with `attempts` 1 and a step with the reason. The same run can take it again at its cap, and it appears in `list_claims_to_work`.
  - [x] **Two failures:** returning it a second time makes it `needs_handler`, and it no longer appears in `list_claims_to_work`.
  - [x] **Not twice:** returning a `decided` or `awaiting_sign_off` claim is 409 and changes nothing. Taking a claim that is not waiting is 409.
  - [x] **The missed-claims check:** `finish_run` is 409 naming CLM-1002 while it is still to work, and 409 while a claim of the run is `in_progress`. Once both are done it finishes with the summary and a finish time.
  - [x] **The to-do list:** `write_todos` replaces the list, keeping order and statuses, and `get_latest_run` returns it. An unknown status is 422.
  - [x] **Recovery:** with a run `running` and a claim `in_progress`, starting the app marks the run `stopped` and returns the claim to `waiting` with `attempts` 1.
- [x] `test_openapi.py` passes with the new operations.
- [x] `npm run reset`, then `curl http://localhost:8000/api/runs/latest` returns `null`, and `curl http://localhost:8000/api/claims` shows 25 claims `waiting`.
- [x] The pre-commit checks pass and the phase is committed.

## Phase 3: The queue agent, its claim agents and the runner

The agent that works the queue, and the code that starts it.

- `agent/queue.py`:
  - `work_claim(run_id, claim_id)`: take the claim; post "Agent started" on a new thread; run the claim agent; then read the claim back. If it is still `in_progress`, or the claim agent raised, call `return_claim` with the reason. Return one line in every case. An error never escapes, so one bad claim never stops the run.
  - The queue agent's tools: `list_claims_to_work`, `write_todos`, `work_claim` and `finish_run`. They reach the run through `ToolRuntime` context (`context_schema` with the `run_id`), so the model never has to pass the run id.
  - `run_queue(run_id)`: the queue agent, with `ModelRetryMiddleware` (5 retries, longer backoff, since a failure here stops the run) and its instructions from `/api/instructions/queue`.
- `backend/instructions/queue.md`: the queue agent's instructions:
  1. List the claims to work and choose an order.
  2. Write the to-do list, one item per claim, plus "Check for missed claims" and "Write the summary".
  3. Work one claim at a time with `work_claim`, updating the list as each starts and ends. A claim back in the queue stays to do; a claim left for a handler is marked so.
  4. Retry returned claims.
  5. Check `list_claims_to_work` is empty.
  6. Finish with a short summary for the handlers: counts by outcome, total paid, payments waiting for sign-off, claims left for a handler.
- `backend/runner.py`:
  - `start_run` creates the run and runs `run_queue` in a background task.
  - `start_agent` creates a run with a cap of 1 and runs `work_claim` and then `finish_run` with its line.
  - If the queue agent raises, or ends without finishing, the runner returns the run's `in_progress` claims and marks the run `stopped` with the reason.
  - `UNDERCOVER_AGENT=off` creates the run but starts nothing (the e2e backend only).
  - The pilot's `run_claim` and `run_queue` go.
- `agent/__main__.py`: `uv run -m agent 5` starts a run capped at 5 and `uv run -m agent CLM-1001` starts one claim, both through the API. It prints the to-do list as it changes, then the summary.

Success criteria. Every test uses stub models, or a fake claim agent passed in:

- [x] **A failed claim does not stop the run:** a queue run of 3 claims, where the claim agent raises on the second, still works the first and third. `work_claim` answers the second with a "failed ... back in the queue" line, and the run finishes.
- [x] **Back in the queue and tried again:** the claim agent fails once on CLM-1002 and succeeds the second time. The queue agent calls `work_claim` on it again and it ends `decided`, with `attempts` 1.
- [x] **Fails twice, left for a handler:** the claim agent always fails on CLM-1002. After two attempts it is `needs_handler`, the `work_claim` line says "left for a handler", and the run still finishes.
- [x] **The cap on a run:** a queue run with cap 2 whose stub tries a third claim gets the refusal back as text. The other 23 claims stay `waiting`.
- [x] **The missed-claims check:** a stub that calls `finish_run` early gets the 409 back as text naming the missed claim. It works that claim and then finishes.
- [x] **Ending without finishing:** a stub that stops without `finish_run` leaves the run `stopped` and no claim `in_progress`.
- [x] **The queue agent fails:** a queue agent that raises leaves the run `stopped` with the error and returns its `in_progress` claim.
- [x] **A fresh start for each claim:** two claims worked in one run have different `thread_id`s on their steps. The claim agent's first model call holds only its instructions and "Decide claim CLM-…", nothing from the earlier claim.
- [x] **One named claim:** `POST /api/claims/CLM-1001/agent`, with a fake claim agent that declines, gives a finished run of cap 1 with the claim `decided`. A second start on it is 409, and a start while a run is running is 409.
- [x] `uv run pytest` and `pyright` pass with coverage at or above 80%.
- [x] The pre-commit checks pass and the phase is committed.

## Phase 4: The queue page: the run, its to-do list and "Needs a handler"

- `dashboard/src/api.ts`: the `Run` and `Todo` types, `needs_handler` in `State`, and `startRun(cap)`, `getLatestRun()` and `getInstructions(agent)`. `workQueue` goes.
- `dashboard/src/RunPanel.tsx` on the queue page:
  - a "Claims to work" number input (starting at 5, from 1 to the number of waiting claims) and "Work the queue", disabled while a run is running
  - the latest run's state: "Running, up to 5 claims", "Finished" or "Stopped" with its reason
  - the to-do list as an ordered list labeled "To-do list", each item with a chip: To do, In progress, Done or Left for a handler
  - the summary once finished
  - polling every two seconds while the run is running
- "Needs a handler" in the status chips, the count tiles and both palettes (Raspberry, and `#CC79A7` in color-blind mode). `docs/ACCESSIBILITY.md`'s table gains the row.
- `playwright.config.ts`: the e2e backend runs with `UNDERCOVER_AGENT=off`, and `e2e/helpers.ts` counts five states.

Success criteria:

- [ ] Vitest: `RunPanel` with a running run shows "Running, up to 5 claims", lists four to-do items with their status words, and disables "Work the queue". With a finished run it shows the summary. Clicking "Work the queue" with the cap set to 3 posts `{"cap": 3}` to `/api/runs`.
- [ ] Vitest: a `needs_handler` claim shows a "Needs a handler" chip and the count tile counts it.
- [ ] E2E `e2e/run.spec.ts`:
  1. On the queue page, set "Claims to work" to 2 and click "Work the queue". The page shows "Running, up to 2 claims".
  2. The test, acting as the agent, writes a to-do list of three items through the API. The page shows them within a few seconds.
  3. The test takes CLM-1001, decides and pays it, and marks its item done. The page shows "Done".
  4. The test finishes the run. The page shows the summary and "Work the queue" is enabled again.
  5. CLM-1002 to CLM-1025 still read "Waiting".
- [ ] E2E: after returning a claim twice through the API, the queue shows it as "Needs a handler" and the counts match the chips.
- [ ] The queue page checked with the Playwright MCP server in light, dark and color-blind modes: the run panel is a rounded panel with no outline, and the chips are readable.
- [ ] The pre-commit checks pass and the phase is committed.

## Phase 5: The claim page and the instructions page

- `Steps.tsx`: steps of kind `read` labeled "Read", folded like long tool results.
- `dashboard/src/SectionsRead.tsx` on the claim page: "Sections read", one line per `read` step (its first line, such as "Claims manual, 9. Repeat claims"), with "None yet" before the agent has read anything.
- `Instructions.tsx`: two read-only panels, "Running the queue" and "Working a claim", from `/api/instructions/queue` and `/api/instructions/claim`.

Success criteria:

- [ ] Vitest: with steps that include two `read` steps, "Sections read" lists exactly those two section names in order.
- [ ] Vitest: the instructions page shows both panels' text and has no textbox or button.
- [ ] E2E: posting a `read` step "Policy wording, 5. Baggage and Personal Effects" to CLM-1018 makes it appear under "Sections read" on its claim page.
- [ ] E2E: the instructions page shows `backend/instructions/queue.md` and `backend/instructions/claim.md`, each in its own panel, and has no textbox or button.
- [ ] Both pages checked with the Playwright MCP server in light and dark modes.
- [ ] The pre-commit checks pass and the phase is committed.

## Phase 6: The docs and a live run of five claims

- `docs/SPEC.md`:
  - the claims manual leaves "Not for now", and decisions follow the wording and the manual, with the wording first
  - "What the team needs to see" gains the run's to-do list and the sections read
  - the states gain "needs a handler"
  - the rules gain the cap on a run and the two-failure rule
- `docs/TECH_STACK.md`: the default model is `deepseek/deepseek-v4.1-flash`. The agent's entry points are `run_queue(run_id)` and `work_claim(run_id, claim_id)`, with the claim agent `run(claim_id, thread_id)` beneath them, and the middleware in use.
- `docs/STATUS.md`: the product as it now is, the five claim states, and how to run a capped run.
- A live run on the default model, as the brief asks:
  1. `npm run reset`, then `npm run dev`.
  2. In the dashboard (Playwright MCP), set "Claims to work" to 5 and click "Work the queue".
  3. Watch the to-do list fill in and be ticked off until the run finishes.

Success criteria:

- [ ] During the live run, the queue page shows the to-do list being written, then items moving from To do to In progress to Done (or Left for a handler), then the summary.
- [ ] After it, exactly five claims have left `waiting`, each decided, waiting for sign-off or needing a handler, and the other 20 are still `waiting`. `GET /api/runs/latest` shows `finished`.
- [ ] Each of the five claim pages shows its steps on one thread per attempt, and a "Sections read" list with at least one section.
- [ ] No claim is left `in_progress`, and no payment over $1,000 was made without a sign-off.
- [ ] `docs/SPEC.md`, `docs/TECH_STACK.md` and `docs/STATUS.md` describe the product as built.
- [ ] `npm run check` is green: ruff, pyright, pytest at or above 80% coverage, Prettier, ESLint, tsc, vitest at or above 80% coverage and Playwright.
- [ ] The phase is committed, and the live run's results are reported to you.
