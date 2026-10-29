# Status

The UnderCover claims pilot, built phase by phase from `docs/PLAN.md`.

## Built so far

- `backend/`: FastAPI and SQLite. On first start it copies the claims, policies, customers and handlers from `data/` into `undercover.db` (or the file named by `UNDERCOVER_DB`). Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `get_instructions` and `list_handlers`. The agent's instructions are in `backend/instructions.md`.
  - The rules are in `backend/rules.py`. `record_decision` takes approve, decline or refer. A decline or referral is decided with a payout of 0. An approval of $1,000 or less stays in progress until `pay_claim` pays it. An approval over $1,000 waits for sign-off: `pay_claim` is refused with 409 until `sign_off` records a handler, which then pays the claim.
  - `add_step` and `list_steps` keep the agent's steps on a claim.
- `agent/`: the UnderCover Agent, LangChain's `create_agent` on OpenRouter. `run(claim_id, thread_id)` fetches its instructions from the backend, works through six tools (one backend call each), and posts every message, tool call and tool result as a step. A refused call (4xx) goes back to the model as text. Run it with `uv run -m agent CLM-1001` while the backend is up.
  - `start_agent` and `work_queue` run the agent in a background task, with "Agent started" and "Agent finished" steps. A run that fails or ends without a decision records why and puts the claim back to `waiting`.
- `dashboard/`: React, Vite and TypeScript in the UnderCover brand. The queue page has a count of claims in each state and the eight-column table. A claim page, opened from `#/claims/CLM-1001`, shows the summary, the decision and payment, the story, items, documents, policy and claim history. Light and dark start in the computer's setting. The "Dark mode" slider in the header, on every page, switches them and the browser remembers the choice (`localStorage` key `undercover-theme`); the mode is the `data-theme` attribute on `<html>`, set by a script in `index.html` before the page draws. `src/api.ts` holds the typed fetch functions.
  - A waiting claim has a "Run the agent" button and the queue has "Work the queue". The claim page shows the agent's steps as a timeline (long tool results fold away) and polls every two seconds while the claim is in progress; the queue polls every two seconds.
  - A claim waiting for sign-off shows a "Payment on hold" panel with a handler picker and "Sign off and pay".
  - `#/instructions` shows the agent's instructions, read only.
- `e2e/`: Playwright tests on their own backend (port 8001, `e2e/e2e.db`, rebuilt by `backend.seed` at the start of each run) and their own Vite (port 5174), so they never touch the data from `npm run dev`.

## Claim states

| State | Meaning |
|---|---|
| `waiting` | In the queue, not yet worked |
| `in_progress` | The agent is working on it |
| `awaiting_sign_off` | Approved over $1,000; payment on hold until a handler signs off |
| `decided` | Declined, referred, or approved and paid |

## Running it

- `npm run dev` starts the backend and the dashboard.
- `uv run -m agent CLM-1001` runs the agent on one claim from the command line, with the backend up.
- `npm run reset` rebuilds the database from `data/`: all 25 claims waiting.
- `npm run check` runs every check.

## Commit guard

`.claude/settings.json` and `.claude/hooks/guard-commit.mjs` stop Claude Code from committing with `--no-verify`, `git commit -n`, `LEFTHOOK=0` or `core.hooksPath`. Blocks go to `~/.claude/blocked-commits.log`, and every `git` command it sees goes to `~/.claude/guard-calls.log`.
