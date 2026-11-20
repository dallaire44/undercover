# Plan: a swarm of claim agents and a scoreboard

The brief is `docs/SWARM.md`. This plan builds on the product as `docs/STATUS.md` describes it after the durable build, in six phases, in the order the brief asks for: the default model and the cost and time, then the dispatcher in place of the queue agent, then starting it from the dashboard, then the evaluations and the scoreboard. Each phase ends green on the pre-commit checks and is committed. Tests never call a model: they use the existing `StubModel` (`agent/tests/conftest.py`) and LangGraph's `InMemorySaver`, so `npm run check` needs no Supabase, Langfuse or OpenRouter.

SIDENOTE: For consistency with the course, please read `labs/week2day4.ipynb` and build the dispatcher in the same style as the lab. Where the lab and this brief differ, follow the brief.

How this plan follows the lab:

- The dispatcher is a `StateGraph` with no model. Its state is a `TypedDict` with a `results` list whose reducer is `operator.add`, as in Part 1.
- A `list_claims` node picks the claims, and a conditional edge, `fan_out`, returns one `Send("work_claim", ...)` per claim.
- `max_concurrency` in the invoke config caps how many claims run at once.
- `work_claim` has a `RetryPolicy`.
- The scores are the lab's: `decision_accuracy`, `accuracy`, the cost of mistakes ($1,500 for a wrongful decline, the payout for a wrongful approval, $50 for a needless referral, the difference for a wrong amount) and `straight_through`. Cost comes from `usage.cost` on each model reply (`response_metadata["token_usage"]["cost"]`), and time from when each claim starts and finishes.
- The lab's challenge has a node after `work_claim` that runs once all the claims are done. The dispatcher uses one, `finish`, to finish the run.

Where the brief differs from the lab, it wins:

- Each claim keeps its own thread and checkpoints, never one shared thread, so a claim can wait days for a sign-off. The dispatcher saves no progress of its own.
- The worker calls one function in the harness, not an agent in the notebook. That function carries on a claim in progress or starts a waiting one.
- The worker's `RetryPolicy` retries only `ModelRateLimitError` and `ModelTimeoutError`, and an `error_handler` leaves a claim in progress when the retries run out, so nothing stops the dispatch.
- The scores are worked out by the backend from its own records, never in the agent. The answer key is in tables only the scoring reads.
- Langfuse gets a tag per run on each claim's trace, not one trace for the whole run.

## The shape of the build

Today a run is the queue agent (`create_agent`) choosing claims one at a time, with a to-do list and a model-written summary. The claim agent is the durable graph from the last build.

After this build:

- **The dispatcher** (`agent/dispatcher.py`, the agent's fifth part) works a run's claims with up to N claim agents at once. It uses no model.
- **A run** is a dispatch of the queue, or an evaluation of a labelled set. The agent's service starts both, and only one runs at a time.
- **The backend** records every model call's tokens and cost and each claim's working time, with the run they happened in. It keeps the answer key, makes an evaluation's copies of the claims, and scores evaluations from its records.
- **The dashboard** starts a dispatch with N on the queue page, and shows the dispatch's claims, its summary, model cost and time. A new Scoreboard page starts evaluations and lists them with their measures.

```mermaid
flowchart LR
    START --> list_claims
    list_claims -- one Send per claim --> work_claim
    work_claim --> finish
    finish --> END
```

- **list_claims** asks the backend for the run's claims to work, oldest submitted first, and leaves out any claim the service is resuming after a sign-off.
- **work_claim** calls `harness.work_claim(run_id, claim_id)` and returns its one-line outcome. It has a `RetryPolicy` on rate limits and timeouts, and an `error_handler`.
- **finish** finishes the run once every claim has come back.

### Choices for you to review

1. **One function in the harness for the dispatcher.** `harness.work_claim(run_id, claim_id)` is the only call the dispatcher makes into the claim agent:
   - It takes the claim with `take_claim`. A waiting claim gets a new thread. A claim already in progress, left by a stopped dispatch, keeps its thread and moves into this run, so it carries on as the same attempt.
   - It runs the claim's graph.
   - A `ModelRateLimitError` or `ModelTimeoutError` goes straight back to the worker with the claim still in progress, so the worker's retry carries it on from its last saved step.
   - Any other error, or an agent that ends without finishing the claim, returns the claim as today (one more attempt). If it went back to `waiting`, the function tries it once more on a new thread in the same dispatch. A second failure leaves it for a handler.
2. **Retries in the worker.** The worker's `RetryPolicy` has `retry_on=(ModelRateLimitError, ModelTimeoutError)` from `langchain_core.exceptions` (`langchain_openai` raises subclasses of both). It makes 3 attempts with waits that start at 5 seconds. When they run out, the worker's `error_handler` (LangGraph's `add_node(..., error_handler=...)`, which receives a `NodeError`) returns the line "CLM-…: still in progress after rate limits, for the next dispatch". The claim stays in progress. The claim graph's own `RetryPolicy` on its model node stays as it is.
3. **A run is a dispatch or an evaluation.** The `runs` table loses `cap` and the `todos` table goes. It gains:
   - `kind` (`dispatch` or `evaluation`) and `agents` (N)
   - `claim_set` (`queue`, `evaluation` or `held_out`) and `tiny`
   - `model` and `reasoning_effort` (`low`, or `none` for a model from `MODEL_NAME`)
   - `reason`, set when a run is stopped, in place of `summary`

   A run on one claim (`uv run -m agent CLM-1001`, or "Run the agent" on a claim page) is a dispatch with N=1 on that claim alone.
4. **The service starts runs, and the backend writes nothing first.** The flow when a handler starts a dispatch:
   1. The dashboard calls the backend's `start_dispatch` with N.
   2. The backend asks the agent's service, through `backend/agent_service.py`, `POST /dispatches` with `{agents}`.
   3. The service takes its run lock without waiting. If it can't, it answers 409, "A dispatch or evaluation is already running". Otherwise it answers 202.
   4. In the background, the service creates the run through the backend's `create_dispatch` (or `create_evaluation`), with the model and the reasoning effort, then runs the dispatcher. It releases the lock when the run is done.

   The backend passes the service's 409 on as its own 409. If the service can't be reached, the backend answers 409, "The agent's service is not running". The dashboard shows either message.

   The backend's `create_dispatch` and `create_evaluation` also refuse while a run is running, as `runs.start` does today.
5. **When the service starts**, it waits for the backend, then stops the run left running, if there is one, with "The agent's service restarted". It no longer carries anything on. A stop no longer returns claims: claims left in progress stay in progress, and the next dispatch carries them on as the same attempts. An evaluation left running shows as stopped, and no dispatch ever carries its copies on.
6. **Resumes and dispatches don't collide.** The service keeps the set of claims it is resuming after a sign-off, and `list_claims` leaves those out.
7. **Cost and time.**
   - The claim graph's model node posts each reply's input and output tokens and `usage.cost` to a new backend operation, `record_model_call`, with the run id from the graph's context. The run id is `null` when no run is working the claim, as on a resume after a sign-off.
   - `run_claim` times each stretch of the graph's work and posts it to `record_work_time`. The graph isn't running while it waits for a sign-off, so the wait is never counted. A stretch that raises still records its time, so failed attempts count.
   - A run's cost is the sum of its model calls. A claim's time in a run is the sum of its stretches in that run. A run's time is from its start to its finish.
8. **Connections.** The backend's limit stays at 4 connections, and so does the agent service's checkpoint pool. Claims wait for a connection rather than fail: the backend's pool and the checkpoint pool both wait up to 120 seconds, in place of the 30-second default.

   `checkpointer()` becomes:
   - `pool()`: one cached pool per process
   - `saver()`: a new `PostgresSaver` on that pool for each claim run, since one saver holds a lock around every read and write

   Without `DATABASE_URL`, `saver()` returns the one cached `InMemorySaver`, so tests still see one store.
9. **The summary is built from the records.** `get_run` returns the run's claims and a `RunSummary`:
   - how many were approved, declined and referred
   - each payout waiting for a sign-off, with its amount
   - the claims left for a handler
   - the claims still in progress

   No model writes it. `finish_run` takes no summary, and it refuses while one of the run's claims is still `waiting`, which keeps the spec's check that a run has not missed a claim.
10. **The answer key and the evaluation's copies.**
    - Seeding loads `data/evals/held_out_claims.json` into a `held_out_claims` table, out of the queue. It loads both sets of handlers' decisions into an `answers` table: `claim_set`, `claim_id`, `decision`, `payout` and `tiny`.
    - `create_evaluation` copies the set's claims (all 25, or the 5 `tiny`) into `claims`, each with a new id, `<run id>-<claim id>` such as `RUN-0007-CLM-1001`, written into its record too. A new `copy_of` column holds the original id.
    - `list_claims` (the queue) and the dispatch's claims to work leave copies out, so the queue's counts never change.
    - `sign_off` refuses a copy with "An evaluation's copy can't be signed off".
    - Only `backend/scores.py` reads `answers`, and no claim operation touches it.
11. **An evaluation's held approvals count as finished.** After a copy's graph pauses for a sign-off, `harness.work_claim` deletes the copy's thread from the checkpointer (`delete_thread`). The copy stays `awaiting_sign_off`, which a run already treats as finished.
12. **The scores.** `backend/scores.py` works out each evaluation's measures from the copies' decisions, model calls and work times, against `answers`:
    - **decision_accuracy:** the share of claims whose decision matches the handler's
    - **accuracy:** the decision matches and the payout is within a dollar
    - **cost of mistakes:** a wrongful decline costs $1,500, a wrongful approval its payout, a needless referral $50, and a wrong amount on a right approval the difference
    - **straight-through rate:** the share of claims not referred
    - **cost per claim**, **time per claim** and **run time**

    A copy the agent didn't decide counts as a referral with a payout of $0.00.
13. **Langfuse.** `tracing(claim_id, thread_id, run_id)` keeps the session per attempt. When there is a run, it also adds `metadata={"langfuse_tags": [run_id]}` to the claim's config, so a whole run is found by its tag.
14. **The default model.** `openai/gpt-6-luna` with low reasoning effort. `MODEL_NAME` still chooses another model, with no reasoning effort, recorded as `none`. `harness.model_settings()` gives the name and the effort, and the service passes both when it creates a run.
15. **What goes:**
    - the queue agent, its middleware and `QUEUE_TOOLS`
    - `RunContext`, `TodoItem` and `write_todos`
    - `backend/instructions/queue.md`, `todos` and the `--cap` option
    - `backend/runner.py`, since the backend no longer creates runs before asking the service
    - the to-do test in `e2e/run.spec.ts`

    `get_instructions` takes only `claim`, and the instructions page shows one panel, "Working a claim". `agent/tools.py` no longer imports the harness, which ends the circular import.
16. **Two notes on the brief against this repo.**
    - The brief's `npm run seed` is this repo's `npm run reset`, which already rebuilds everything. It now drops the old `todos` table too, along with the rest of the schema on Supabase.
    - The brief names `docs/CODE_STANDARDS.md` rules 10 and 13. In this repo's numbering, those are rule 8 (the agent's parts, now five) and the closing paragraph on what the structure tests check.

    The brief also says to leave the spec's Rules alone, so "A run never works more claims than its cap" stays as written, though dispatches have no cap. Please say if you'd like that rule reworded.

## The API after this build

New or changed backend operations. Each has an `operation_id`, a one-line docstring and no optional inputs (a nullable field such as `run_id` is still required), and `backend/tests/test_openapi.py` keeps checking them.

| Operation | Route | Used by | What it does |
|---|---|---|---|
| `start_dispatch` | `POST /api/dispatches/start` `{agents}` | dashboard | Asks the service to start a dispatch with N claim agents (1 to 25). 202, or 409 with the reason |
| `start_evaluation` | `POST /api/evaluations/start` `{agents, claim_set, tiny}` | dashboard | Asks the service to start an evaluation. 202, or 409 with the reason |
| `start_agent` | `POST /api/claims/{claim_id}/agent` | dashboard, CLI | Asks the service to work one waiting claim. 202, or 409 |
| `create_dispatch` | `POST /api/dispatches` `{agents, model, reasoning_effort}` | service | Creates the run, refusing while one is running |
| `create_evaluation` | `POST /api/evaluations` `{agents, claim_set, tiny, model, reasoning_effort}` | service | Creates the run and its copies |
| `list_claims_to_work` | `GET /api/runs/{run_id}/claims-to-work` | service | A dispatch: the queue's claims in progress and waiting. An evaluation: its copies still to work. Oldest submitted first |
| `take_claim` | `POST /api/runs/{run_id}/claims/{claim_id}` | service | A waiting claim gets a new thread. One in progress keeps its thread and joins the run |
| `record_model_call` | `POST /api/claims/{claim_id}/model-calls` `{run_id, input_tokens, output_tokens, cost}` | service | Records one model call |
| `record_work_time` | `POST /api/claims/{claim_id}/work-times` `{run_id, started_at, seconds}` | service | Records one stretch of work on a claim |
| `get_run`, `get_latest_dispatch` | `GET /api/runs/{run_id}`, `GET /api/dispatches/latest` | dashboard, service | The run with its claims, `RunSummary`, cost and time |
| `finish_run` | `POST /api/runs/{run_id}/finish` | service | No summary in the request now |
| `stop_run` | `POST /api/runs/{run_id}/stop` `{reason}` | service | Marks the run stopped, and leaves its claims as they are |
| `list_evaluations` | `GET /api/evaluations` | dashboard | Every evaluation, newest first, with its measures |
| `get_evaluation` | `GET /api/evaluations/{run_id}` | dashboard | One evaluation with each claim scored against the handler's decision |

Gone: `start_run`, `write_todos`, `get_latest_run` (now `get_latest_dispatch`) and `get_instructions` for `queue`.

The agent's service:

| Operation | Route | What it does |
|---|---|---|
| `health` | `GET /health` | The service is up |
| `start_dispatch` | `POST /dispatches` `{agents}` | 202, or 409 while a run is going. Creates the dispatch and works it |
| `start_evaluation` | `POST /evaluations` `{agents, claim_set, tiny}` | 202, or 409. Creates the evaluation and works it |
| `work_one` | `POST /claims/{claim_id}/work` | 202, or 409. A dispatch with N=1 on one claim |
| `resume_claim` | `POST /claims/{claim_id}/resume` | 202. Picks a signed-off claim back up and pays it |

---

## Phase 1: GPT-6 Luna by default, and cost and time for every claim

The new default model, and cost and time recorded on the product as it is, with the queue agent still in place.

- `agent/harness.py`:
  - `DEFAULT_MODEL = "openai/gpt-6-luna"`
  - `model_settings()` returns the name and the effort (`low`, or `none` with `MODEL_NAME`)
  - `ClaimContext` gains `run_id: str | None`
  - the **agent** node posts each reply's tokens and cost with `api.record_model_call`
  - `run_claim` takes the run id, times each stretch of the graph's work and posts it with `api.record_work_time`, in a `finally`
- `backend/db.py`: `model_calls` (id, `claim_id`, `run_id`, `input_tokens`, `output_tokens`, `cost`, `called_at`) and `work_times` (id, `claim_id`, `run_id`, `started_at`, `seconds`).
- `backend/usage.py`: record a model call and a stretch of work, and total a run's cost and a claim's time in a run.
- `backend/models.py` and `backend/main.py`: `record_model_call` and `record_work_time`.
- `agent/api.py`: the two calls.
- `agent/tests/conftest.py`: `StubModel` replies carry `response_metadata={"token_usage": {"cost": …}}` and `usage_metadata`, so tests see a cost.

Success criteria:

- [x] With `MODEL_NAME` unset, `harness.model()` is `openai/gpt-6-luna` with `reasoning_effort="low"`, and `model_settings()` is `("openai/gpt-6-luna", "low")`. With `MODEL_NAME=openrouter/free`, the effort is `None` and the settings say `"none"`.
- [x] A stub claim run on CLM-1001 with three model replies costing $0.01 each, inside a run, records three model calls with that run's id, their tokens, and a cost of $0.03.
- [x] **A wait for a sign-off is left out:**
  1. A stub run approves CLM-1003 over the limit and pauses.
  2. The test signs off, then sleeps 1 second, then resumes.
  3. The claim has two work times: the first with the run's id, and the resume's with `null`. Their sum is less than the time from the first start to the payment by at least the 1-second wait.
- [x] **A failed attempt counts:** a stub that raises `RuntimeError` after one model call still leaves one model call and one work time on the claim, with the run's id.
- [x] `test_openapi.py` passes with the two new operations.
- [x] Code: the model settings are in `agent/harness.py`, the calls in `agent/api.py`, and the records in `backend/usage.py`. Nothing outside `backend/usage.py` writes `model_calls` or `work_times`.
- [x] The pre-commit checks pass and the phase is committed.

## Phase 2: The dispatcher in place of the queue agent

The dispatcher works the queue, driven from the agent's service as runs are today. The dashboard's start comes in Phase 3.

- `agent/dispatcher.py`:
  - `Dispatch` (the state: `run_id`, `claim_ids`, `results`)
  - the nodes `list_claims`, `work_claim` and `finish`, and the edge `fan_out`
  - `RetryPolicy` and `error_handler` on `work_claim`
  - `dispatcher()` builds the graph with no checkpointer
  - `dispatch(run_id, agents, skip, only)` invokes it with `{"max_concurrency": agents}`. `only` is the one claim of a run on one claim.
- `agent/harness.py`:
  - `work_claim(run_id, claim_id)` (choice 1)
  - `pool()` and `saver()` (choice 8)
  - `tracing` with the run's tag (choice 13)
  - deleting a copy's thread when it pauses (choice 11, used from Phase 4)
  - The queue agent, its middleware, `run_queue`, `work_run`, `work_one`, `carry_on`, `pick_up` and `has_queue_thread` go.
- `agent/tools.py`: the queue agent's tools and `RunContext` go.
- `backend/runs.py`:
  - runs gain the new columns (choice 3) and lose the cap
  - `take_claim` carries on a claim in progress (choice 1)
  - `claims_to_work` orders by submitted date and leaves out copies
  - `finish` builds no summary and refuses while a claim of the run is waiting
  - `stop` leaves the claims as they are
  - `get` returns the run's claims, `RunSummary`, cost and time
- `backend/db.py`: `todos` goes. `backend/instructions/queue.md` goes.
- `backend/db.py` and `agent/harness.py`: each pool waits up to 120 seconds for a connection.

Success criteria. Every test uses stub models and `InMemorySaver`:

- [x] **Never more than N at once:**
  1. A test patches `harness.work_claim` with a stand-in that sleeps 0.2 seconds and records how many are running.
  2. A dispatch of 10 claims at N=3 never has more than 3 running, and works all 10.
  3. At N=1, the claims are worked oldest submitted first.
- [x] **A dispatch works what is left:** with CLM-1003 in progress on a thread from an earlier, stopped run, a dispatch works it first, on the same thread with `attempts` unchanged, then the waiting claims. At the end the run is `finished` and no claim is `waiting`.
- [x] **A rate limit carries on as the same attempt:**
  1. A stub raises `ModelRateLimitError` on its third model call, once.
  2. With the retry wait patched to 0, the claim is decided on its first thread, with `attempts` 0 and one decision.
  3. The stub's next call after the error sees the earlier tool results.
- [x] **Retries run out without stopping the dispatch:**
  1. On a dispatch of three claims, a stub for CLM-1001 always raises `ModelTimeoutError`.
  2. CLM-1001 stays `in_progress` with its thread, `attempts` 0, and the line "still in progress".
  3. The other two claims are decided, and the run finishes with CLM-1001 under "still in progress" in its summary.
- [x] **A failure is tried once more in the same dispatch:** a stub that raises `RuntimeError` on CLM-1001's first attempt and decides on its second leaves CLM-1001 decided with `attempts` 1, on a second thread. One that fails twice leaves it `needs_handler`. The dispatch finishes either way.
- [x] **No claim decided or paid twice:** across the tests above, each claim has at most one row in `decisions` and in `payments`.
- [x] **The summary is built from the records:** after a stub dispatch of 4 claims (one approved and paid, one approved over the limit, one declined, one failing twice), `get_run` gives `approved: 2, declined: 1, referred: 0`, the held payout with its amount, the claim left for a handler, and nothing in progress.
- [x] **A claim being resumed is skipped:** a dispatch with CLM-1003 in the skip set never takes it.
- [x] **Langfuse:** with the keys set, `tracing("CLM-1001", "t1", "RUN-0002")` has `metadata.langfuse_tags == ["RUN-0002"]` and the session `CLM-1001 t1`. With no run, there are no tags.
- [x] **Its own saver per claim:** with `DATABASE_URL` set, two `saver()` calls give different `PostgresSaver`s on the same pool, built without connecting. Without it, both are the same `InMemorySaver`.
- [x] The service's `work_one` on a waiting claim creates a dispatch with N=1, works that claim alone and finishes the run with it.
- [x] `grep -rn "queue_middleware\|QUEUE_TOOLS\|write_todos\|todos" agent backend` finds nothing.
- [x] Code:
  - [x] the dispatcher is in `agent/dispatcher.py` and calls the harness only through `harness.work_claim`
  - [x] `test_structure.py` checks that `dispatcher.py` imports nothing from `agent.tools` and names no other harness function
  - [x] `langgraph.checkpoint` is still imported only in `agent/harness.py`
- [x] The pre-commit checks pass and the phase is committed.

Changes while building Phase 2:

- **LangGraph 1.2.23.** On 1.2.12, a node's `error_handler` ran for a node reached by `Send`, but the error was raised again and stopped the graph. 1.2.23 fixes this, so `langgraph>=1.2.23` is now a direct dependency (committed in Phase 1).
- **The handler takes the claim alone.** LangGraph's types for `error_handler` don't include the `(state, error: NodeError)` form, so `left_in_progress` takes the task only. The error isn't needed: the dispatcher's lines aren't stored or shown.
- **The run's tag goes through `propagate_attributes`.** A claim graph run inside the dispatcher's node has a parent run (checked with a callback), and Langfuse reads `langfuse_tags` in the metadata only at a trace's root. So `tracing` passes `tags=[run_id]` to `propagate_attributes`, beside the session, as the last build did for the session.
- **The rate-limit test raises three times.** The claim graph's own `RetryPolicy` on the model node also retries rate limits (two retries), so the stub raises `ModelRateLimitError` on three calls in a row to reach the dispatcher's retry.
- **Claims in progress come first.** `list_claims_to_work` gives the claims in progress first, then the waiting ones, each oldest submitted first.

## Phase 3: Starting a dispatch from the dashboard

- `agent/service.py`:
  - `start_dispatch`, `work_one` and `resume_claim` (choice 4)
  - a run lock, held from the request to the end of the run
  - the set of claims being resumed (choice 6)
  - on startup, stopping the run left running (choice 5)
- `backend/agent_service.py`: `start_dispatch(agents)` and `work_one(claim_id)` raise `Refused` with the service's reason, or with "The agent's service is not running". `resume_claim` keeps its log-and-carry-on behavior.
- `backend/main.py`: `start_dispatch`, `start_agent`, `create_dispatch`, `get_latest_dispatch` and `stop_run`. `backend/runner.py` goes.
- `agent/cli.py`: `uv run -m agent CLM-1001` (one positional claim id) starts a run on one claim and prints each change to its claims, then how it ended. Without a claim id it prints the usage.
- `dashboard/src/RunPanel.tsx`:
  - "Claim agents at once", 1 to 25, starting at 3
  - "Dispatch the queue", and the refusal shown when there is one
  - the latest dispatch: "Running, 3 claim agents at once", "Finished" or "Stopped" with the reason
  - each of its claims with a status chip and a link
  - its model cost and time
  - its summary once finished
  - It polls every two seconds, as the queue does.
- `dashboard/src/Instructions.tsx`: the one panel, "Working a claim".
- `dashboard/src/api.ts`: the new types and calls. A refused start returns the backend's reason.
- `e2e/agent-stand-in.mjs` records each request's body too. `e2e/run.spec.ts`:
  - the to-do test is replaced by a dispatch started on the dashboard
  - a test that plays out a dispatch through the API, as the service would, and checks the panel

Success criteria:

- [x] Agent service tests (TestClient on `agent.service.app`, with the dispatcher patched):
  - [x] `POST /dispatches {"agents": 3}` answers 202 and runs one dispatch at N=3
  - [x] a second start while it runs is 409 "A dispatch or evaluation is already running"
  - [x] once the first ends, a start is taken again
  - [x] every operation follows the API rules
- [x] On startup with a run left `running`, the service stops it with "The agent's service restarted", and its claims in progress stay in progress.
- [x] Backend tests: `start_dispatch` passes `{agents: 3}` to the service. A 409 from the service comes back as 409 with its reason. An unreachable service is 409 "The agent's service is not running". `agents` of 0 or 26 is 422.
- [x] Agent test, end to end on stub models: `start_dispatch` through the backend, with the service in the same process, works 3 claims and finishes the dispatch. `GET /api/dispatches/latest` shows the claims, the summary, a model cost above $0.00 and a time.
- [x] Vitest:
  - [x] the panel starts at 3 and limits N to 1–25
  - [x] it shows each claim with its chip, the cost as $0.04 and the time as "1 min 12 s"
  - [x] it shows the summary once finished
  - [x] a refusal shows its reason
  - [x] the instructions page has one panel
- [x] E2E:
  - [x] "Dispatch the queue" with 5 claim agents reaches the stand-in as `POST /dispatches {"agents":5}`
  - [x] a dispatch played out through the API shows "Running, 3 claim agents at once", its claims' chips changing, then "Finished" with its summary
- [x] Checked in the browser with the Playwright MCP server: the run panel in light and dark mode, with screenshots reviewed.
- [x] Code: the backend reaches the service only through `backend/agent_service.py`, and the dashboard reaches the service only through the backend (`test_structure.py`: no `8002` or `/dispatches` path outside `backend/agent_service.py` and `dashboard/src/api.ts`'s `/api/` calls).
- [x] The pre-commit checks pass and the phase is committed.

Changes while building Phase 3:

- The service's run lock and its 409, the backend's relay of a refusal and "The agent's service is not running", `start_agent` and the CLI were built in Phase 2, since the backend's old way of creating runs first went with the queue agent.
- The panel's time is the dispatch's own time, from its start to its finish (or now), as the brief asks. Each claim's working time is in the API, and shows on the scoreboard in Phase 5.
- A refusal is marked with a bar in the alert color, since text in that color would be too faint on the light theme.

## Phase 4: Evaluations

- `backend/db.py`:
  - `held_out_claims` and `answers`, seeded from `data/evals/` (choice 10)
  - `claims` gains `copy_of`
- `backend/evaluations.py`: `create` makes the run and its copies.
- `backend/scores.py`: the measures (choice 12), the only reader of `answers`.
- `backend/records.py` leaves copies out of `list_claims`. `backend/rules.py` refuses a sign-off on a copy.
- `backend/main.py`: `start_evaluation`, `create_evaluation`, `list_evaluations` and `get_evaluation`.
- `agent/service.py`: `start_evaluation`, under the same run lock.
- `agent/harness.py`: a copy that pauses for a sign-off has its thread deleted (choice 11).

Success criteria:

- [x] Seeding gives 25 waiting claims in the queue, 25 rows in `held_out_claims`, and 50 rows in `answers`, 10 of them `tiny`.
- [x] **The queue stays as it was:**
  1. `list_claims` before an evaluation of the evaluation set equals `list_claims` after it, with every copy decided by stubs.
  2. A dispatch started after the evaluation lists no copy.
- [x] **Copies:**
  - [x] a tiny held-out evaluation has 5 copies, each with an id such as `RUN-0002-CLM-11xx` in its record, and `copy_of` set
  - [x] `GET /api/claims/<copy id>` has the claim's story and nothing from the handlers' decisions: none of the handler's reason, calculation, `tests` or `difficulty` text appears in it
- [x] **No sign-off on a copy:** on a copy approved over the limit, `sign_off` is 409 "An evaluation's copy can't be signed off".
- [x] **Held approvals count as finished:** in a stub evaluation where one copy is approved over the limit, the evaluation finishes. The copy is `awaiting_sign_off`, and the checkpointer has no checkpoint for its thread.
- [x] **The measures match ones worked out by hand:** an evaluation of the 5 tiny claims of the evaluation set, with decisions recorded through the API, gives the hand-worked `decision_accuracy`, `accuracy`, cost of mistakes, straight-through rate, cost per claim, time per claim and run time. The decisions are:
  - one right
  - one approved with the right decision and a payout $20 off
  - one wrongful decline
  - one needless referral
  - one left undecided

  The test states the expected values and how each was worked out.
- [x] An evaluation that the service's startup stopped shows `stopped`, and a later dispatch never takes its copies.
- [x] Each evaluation records its set, `tiny`, N, the model and the reasoning effort.
- [x] Code:
  - [x] `test_structure.py` checks that `answers` appears only in `backend/db.py` and `backend/scores.py`
  - [x] `agent/` never names `/api/evaluations/{` or `answers`
- [x] The pre-commit checks pass and the phase is committed.

Changes while building Phase 4:

- A copy's `get_claim` is checked to have exactly the original claim's fields, with no decision, and none of the handler's reason, `tests` or `difficulty` text. A calculation step's text, such as "Duffel bag", is often an item on the claim itself, so it can't be checked as text.
- `get_evaluation` and `list_evaluations` give the run, its measures (`scores`) and its scored copies.

## Phase 5: The scoreboard

- `dashboard/src/Scoreboard.tsx` at `#/scoreboard`, linked from the header:
  - **Start an evaluation:**
    - the set: "Evaluation set" or "Held-out set"
    - "Only the five tiny claims"
    - "Claim agents at once", 1 to 25, starting at 3
    - the refusal shown when there is one
  - **Evaluations,** newest first, one row each:
    - set, N, model and effort, status
    - decision accuracy, accuracy, cost of mistakes, straight-through rate
    - cost per claim, time per claim, run time
- `dashboard/src/Evaluation.tsx` at `#/scoreboard/RUN-0007`:
  - each claim, linked to its copy's page
  - the handler's decision and payout beside the agent's
  - a miss marked with the alert color and the word "Miss", so it doesn't rest on color alone
  - each claim's cost and time
- `dashboard/src/Claim.tsx`: a copy says "A copy of CLM-1001 in evaluation RUN-0007", with no "Run the agent" and no sign-off form.
- `e2e/run.spec.ts` gains the scoreboard test, in the same file as the dispatch tests, because only one run goes at a time and the tests in one file run in order.

Success criteria:

- [x] Vitest:
  - [x] the scoreboard lists evaluations newest first, with percentages such as "80%" and money such as "$1,550.00"
  - [x] the start form sends the set, `tiny` and N
  - [x] an evaluation's page marks a miss with "Miss" and links each copy
  - [x] a copy's claim page has no sign-off form and no "Run the agent"
- [x] E2E:
  - [x] "Start an evaluation" with the held-out set, tiny, and 5 claim agents reaches the stand-in as `POST /evaluations` with `{"agents":5,"claim_set":"held_out","tiny":true}`
  - [x] an evaluation played out through the API, as `e2e/run.spec.ts` plays out a dispatch, shows on the scoreboard with every measure
  - [x] its page shows the handler's and the agent's decisions with the misses marked
  - [x] the queue page's counts are the same before and after
- [x] Checked in the browser with the Playwright MCP server: the scoreboard, an evaluation and a copy's page, in light and dark mode, at 1280 px wide, with screenshots reviewed.
- [x] Code: the scoreboard's calls are in `dashboard/src/api.ts`. Each page is its own module. The brand's colors come from the existing variables.
- [x] The pre-commit checks pass and the phase is committed.

Changes while building Phase 5:

- "Claim agents at once" is one component, `AgentsField.tsx`, used by the run panel and the scoreboard. The names of the sets and run states live in `format.ts`, beside the claim states.
- The queue table's rule that its second column is at least 15rem wide made the scoreboard scroll at 1280 px, so the scoreboard's and an evaluation's tables have a class of their own, `scores`.
- The header has one more link, so the keyboard test in `e2e/theme.spec.ts` tabs five times to reach the dark-mode slider.

## Phase 6: The docs, and live runs on Supabase

- `docs/SPEC.md`:
  - the section on working the queue describes dispatches with N claim agents and what happens to problems
  - the section on what the team needs to see describes the dispatch's claims, summary, cost and time, and the scoreboard
  - the Rules are left alone
- `docs/TECH_STACK.md`:
  - the dispatcher is the agent's fifth part
  - the default model is GPT-6 Luna
  - cost and time are recorded
  - evaluations are scored by the backend
  - Langfuse tags runs
- `docs/CODE_STANDARDS.md`:
  - rule 8 names five parts
  - the closing paragraph lists the new structure checks
- `docs/PROCESS.md`: the live runs below replace the five-claim cap.
- `docs/STATUS.md`: the product as it now is, and the live runs.
- Live runs, after one `npm run reset`, with `npm run dev` and the default model, through the Playwright MCP server. About 55 claims in all, a few cents each:
  1. Start a dispatch at N=3. After a few claims have started, `kill -9 $(lsof -ti tcp:8002)`, which makes `npm run dev` stop the others, then start `npm run dev` again.
  2. Start a dispatch at N=25. Sign off a claim held for sign-off.
  3. During it, count the connections through the Supabase MCP server.
  4. Run an evaluation of the evaluation set at N=25, and one of the held-out set's five tiny claims at N=5.
  5. Find the N=25 dispatch's claims in Langfuse by its tag.

Success criteria:

- [ ] Run 2 carries on the claims left in progress by run 1, as the same attempts (same `thread_id`, `attempts` unchanged, one decision each). It works the rest with 25 at once: the claims' first work times start within a few seconds of each other.
- [ ] Run 2's time is well under the sum of its claims' times.
- [ ] Comparing claims worked from the start, each takes about as long at N=25 as at N=3. If they are slower, the report says where the time goes, keeping to 4 connections.
- [ ] Claims held for sign-off wait. A sign-off on the dashboard shows the claim paid within five seconds.
- [ ] No claim fails for want of a database connection.
- [ ] During run 2, `select count(*) from pg_stat_activity where usename = 'postgres'` through the Supabase MCP server returns 12 or fewer.
- [ ] Both evaluations appear on the scoreboard with every measure. The queue page's counts are the same before and after them.
- [ ] Through Langfuse's v2 observations API, the traces tagged with run 2's id cover each of its claims.
- [ ] `docs/SPEC.md`, `docs/TECH_STACK.md`, `docs/PROCESS.md`, `docs/CODE_STANDARDS.md` and `docs/STATUS.md` describe the product as built.
- [ ] With `.env` moved out of the way, `npm run check` is green:
  - ruff
  - pyright
  - pytest at or above 80% coverage
  - Prettier, ESLint and tsc
  - vitest at or above 80% coverage
  - Playwright
- [ ] The phase is committed, and the live runs' results are reported to you.
