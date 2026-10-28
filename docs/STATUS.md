# Status

The pilot is being built in the phases of `docs/PLAN.md`. Built so far:

- `backend/`: FastAPI and SQLite. Phases 0 to 5: the records and the read operations (`list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `get_instructions`, `list_handlers`, `list_steps`), the write operations (`record_decision`, `pay_claim`, `sign_off`, `add_step`) with the payment rules in `backend/rules.py`, `start_agent` and `work_queue`, which run the agent in the background (`backend/runs.py`), and the agent's instructions in `backend/instructions.md`. The database, `undercover.db` (or `UNDERCOVER_DB`), is seeded from `data/` on first use. `npm run reset` rebuilds it.
- `agent/`: the UnderCover Agent, LangChain's `create_agent` with six tools that each call one backend operation. Its instructions come from `GET /api/instructions`, and each message, tool call and tool result is posted to the claim's steps. Run it on one claim with `uv run -m agent CLM-1001` (the backend must be running; `BACKEND_URL` defaults to `http://localhost:8000`). It uses `openai/gpt-6-luna`, or `MODEL_NAME` if set, with `OPENROUTER_API_KEY` from `.env`.
- `dashboard/`: React, Vite and TypeScript, in UnderCover's brand, in light and dark. A "Dark mode" switch in the header, on every page, changes the mode and remembers the choice in the browser (`localStorage`, key `undercover-theme`). Until it is used, each load follows the computer's setting. The mode is the `data-theme` attribute on `<html>`, set by a few lines in `dashboard/index.html` before the page draws. A "Color-blind mode" switch next to it, off by default, changes the claim-state, decision and payment-on-hold colors to the Okabe-Ito colors in `docs/ACCESSIBILITY.md` and adds a check, a cross or an arrow to each decision chip. It works in light and dark, is remembered under `undercover-colors`, and is the `data-colors` attribute on `<html>`. Both switches are one component, `dashboard/src/ModeSwitch.tsx`. Phases 4 to 5, 7 and 8: the queue (a count of claims in each state and a table with the eight columns in `docs/SPEC.md`) and each claim in full, at hash links such as `#/claims/CLM-1001`. On a waiting claim, "Run the agent" starts it, and "Work the queue" on the queue page runs it on every waiting claim. A timeline of the agent's steps appears on the claim and refreshes every two seconds while the agent works, and the queue refreshes every two seconds. A claim waiting for sign-off shows the payment on hold, with a handler picker and "Sign off and pay". "Agent instructions" in the header opens the agent's instructions, read only. `dashboard/src/api.ts` holds the typed calls to the backend. The Vite proxy points at `http://127.0.0.1:8000`, or at `API_URL` if it is set.
- `e2e/`: Playwright tests of the queue, the claim page, the sign-off, the steps and the instructions page. They run their own backend on port 8001 with its own database, `e2e/e2e.db`, rebuilt by `backend.seed` at the start of each run, and their own Vite on port 5174, so they never touch the data in `npm run dev`.

## How to run it

- `uv sync` and `npm install` once. The agent needs `OPENROUTER_API_KEY` in `.env`.
- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173. Open http://localhost:5173.
- `npm run reset` rebuilds the database from `data/`, so all 25 claims are waiting again.
- `uv run -m agent CLM-1001` runs the agent on one claim from the command line, with the backend running.
- `npm run check` runs every check. The Playwright tests use ports 8001 and 5174, so they run beside `npm run dev`.

## Claim states

| State | Label | Meaning |
|---|---|---|
| `waiting` | Waiting | In the queue, not yet worked. All 25 claims start here. |
| `in_progress` | In progress | The agent is working on it. |
| `awaiting_sign_off` | Waiting for sign-off | Approved over $1,000. The payment is blocked until a handler signs off. |
| `decided` | Decided | Declined, referred, or approved and paid. |

If an agent run fails or ends without a decision, the claim goes back to waiting, with a step that says why.

## Commit guard

`.claude/settings.json` and `.claude/hooks/guard-commit.mjs` hold a Claude Code `PreToolUse` hook, from `docs/CLAUDE_PRE_TOOL_USE_HOOK.md`. It blocks Bash commands that would skip the pre-commit checks (`--no-verify`, `git commit -n`, `LEFTHOOK=0`, `core.hooksPath`) and logs each block to `~/.claude/blocked-commits.log`. Every `git` command it sees goes to `~/.claude/guard-calls.log`, with `blocked` true or false, so a missing line means the hook was not called. Claude Code reads it from the folder where a session starts, so start sessions at the repo root.
