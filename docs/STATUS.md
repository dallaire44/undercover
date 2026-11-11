# Status

The UnderCover claims pilot, built from `docs/PLAN.md`, and the agent's harness, being built from `docs/PLAN_HARNESS.md` (Phases 1 to 3 of 6 done).

## Built so far

- `backend/`: FastAPI and SQLite. On first start it copies the claims, policies, customers and handlers from `data/` into `undercover.db` (or the file named by `UNDERCOVER_DB`). Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_instructions` and `list_handlers`. The claim agent's instructions are in `backend/instructions/claim.md`, served at `/api/instructions/claim`.
  - `backend/documents.py` splits the policy wording and the claims manual into numbered sections: `list_sections` (the contents of both), `search_documents` (the sections that best match a few words, each with its best line) and `read_section` (one section, headed such as `Claims manual, 9. Repeat claims`). The whole wording is no longer served.
  - The rules are in `backend/rules.py`. `record_decision` takes approve, decline or refer. A decline or referral is decided with a payout of 0. An approval of $1,000 or less stays in progress until `pay_claim` pays it. An approval over $1,000 waits for sign-off: `pay_claim` is refused with 409 until `sign_off` records a handler, which then pays the claim.
  - `add_step` and `list_steps` keep the agent's steps on a claim.
  - `backend/runs.py`: a run works the queue up to a cap of claims. `take_claim` moves a waiting claim into the run and in progress, and refuses past the cap; a claim the run returned stays in the run, so its retry does not use up the cap. `return_claim` follows a failed attempt: attempts plus one, then back to `waiting`, or `needs_handler` after two. `write_todos` replaces the run's to-do list (to do, in progress, done, left for a handler). `finish_run` refuses while a claim of the run is in progress or `list_claims_to_work` is not empty. `get_run` and `get_latest_run` read runs. One run at a time. On startup the backend stops any run left running and returns its claims in progress.
- `agent/`: the UnderCover Agent, LangChain's `create_agent` on OpenRouter. `agent/model.py` holds the model, `deepseek/deepseek-v4.1-flash` with low reasoning effort, or `MODEL_NAME` if set, and the claim agent's middleware: `ModelRetryMiddleware` (two retries with backoff, then an error) and `ModelCallLimitMiddleware` (an error past 30 model calls). The OpenAI client's own retries are off, so the middleware is the one place retries happen. `agent/claim.py` `run(claim_id, thread_id)` fetches its instructions from the backend, works through eight tools (one backend call each, including the three document lookups), and posts every message, tool call and tool result as a step; a `read_section` result is a step of kind `read`. A refused call (4xx) goes back to the model as text.
  - `agent/queue.py`: the queue agent, `run_queue(run_id)`, works a run with four tools: `list_claims_to_work` (headed with how many more claims the cap allows), `write_todos`, `work_claim` and `finish_run`. Its tools reach the run id through `ToolRuntime` context, and `ModelRetryMiddleware` retries its model calls five times. Its instructions are `backend/instructions/queue.md`.
  - `work_claim(run_id, claim_id)` is plain code: it takes the claim into the run, posts "Agent started", runs a fresh claim agent on a new thread, and posts "Agent finished" once the claim has left `in_progress`. Otherwise, or if the claim agent raised, it calls `return_claim` with the reason. It always answers in one line, such as `CLM-1001: approved, $420.00 paid`.
  - `backend/runner.py`: `start_run` (`POST /api/runs`, with a cap) runs the queue agent in a background task, and `start_agent` on one claim starts a run with a cap of 1 that calls `work_claim` alone. A run whose agent fails or ends without finishing is stopped and its claims in progress are returned. `UNDERCOVER_AGENT=off` creates runs without starting the agent.
- `dashboard/`: React, Vite and TypeScript in the UnderCover brand. The queue page has a count of claims in each state and the eight-column table. A claim page, opened from `#/claims/CLM-1001`, shows the summary, the decision and payment, the story, items, documents, policy and claim history. Light and dark start in the computer's setting. The "Dark mode" slider in the header, on every page, switches them and the browser remembers the choice (`localStorage` key `undercover-theme`); the mode is the `data-theme` attribute on `<html>`, set by a script in `index.html` before the page draws. `src/api.ts` holds the typed fetch functions.
  - A waiting claim has a "Run the agent" button and the queue has "Work the queue". The claim page shows the agent's steps as a timeline (long tool results fold away) and polls every two seconds while the claim is in progress; the queue polls every two seconds.
  - A claim waiting for sign-off shows a "Payment on hold" panel with a handler picker and "Sign off and pay".
  - The "Color-blind mode" slider next to "Dark mode" switches the claim-state, decision and payment-on-hold colors to the Okabe-Ito palette and adds a check, cross or arrow to each decision chip (`data-colors` on `<html>`, key `undercover-colors`, off by default). The two sliders are independent. See `docs/ACCESSIBILITY.md`.
  - `#/instructions` shows the agent's instructions, read only.
- `e2e/`: Playwright tests on their own backend (port 8001, `e2e/e2e.db`, rebuilt by `backend.seed` at the start of each run) and their own Vite (port 5174), so they never touch the data from `npm run dev`.

## Claim states

| State | Meaning |
|---|---|
| `waiting` | In the queue, not yet worked |
| `in_progress` | The agent is working on it |
| `awaiting_sign_off` | Approved over $1,000; payment on hold until a handler signs off |
| `decided` | Declined, referred, or approved and paid |
| `needs_handler` | Failed twice; left for a handler |

## Running it

- `npm run dev` starts the backend and the dashboard.
- `uv run -m agent 5` starts a run capped at five claims and `uv run -m agent CLM-1001` a run on one claim, both through the API with the backend up. Each prints the to-do list as it changes, then how the run ended.
- `npm run reset` rebuilds the database from `data/`: all 25 claims waiting. Run it once after pulling this build, since the tables changed.
- `npm run check` runs every check.

## Commit guard

`.claude/settings.json` and `.claude/hooks/guard-commit.mjs` stop Claude Code from committing with `--no-verify`, `git commit -n`, `LEFTHOOK=0` or `core.hooksPath`. Blocks go to `~/.claude/blocked-commits.log`, and every `git` command it sees goes to `~/.claude/guard-calls.log`.
