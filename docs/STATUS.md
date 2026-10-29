# Status

The UnderCover claims pilot, built phase by phase from `docs/PLAN.md`.

## Built so far

- `backend/`: FastAPI and SQLite. On first start it copies the claims, policies, customers and handlers from `data/` into `undercover.db` (or the file named by `UNDERCOVER_DB`). Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `get_instructions` and `list_handlers`. The agent's instructions are in `backend/instructions.md`.
  - The rules are in `backend/rules.py`. `record_decision` takes approve, decline or refer. A decline or referral is decided with a payout of 0. An approval of $1,000 or less stays in progress until `pay_claim` pays it. An approval over $1,000 waits for sign-off: `pay_claim` is refused with 409 until `sign_off` records a handler, which then pays the claim.
  - `add_step` and `list_steps` keep the agent's steps on a claim.
- `agent/`: still the hello-world agent.
- `dashboard/`: still one page that shows whether the backend is up.
- `e2e/`: one test of that page.

## Claim states

| State | Meaning |
|---|---|
| `waiting` | In the queue, not yet worked |
| `in_progress` | The agent is working on it |
| `awaiting_sign_off` | Approved over $1,000; payment on hold until a handler signs off |
| `decided` | Declined, referred, or approved and paid |

## Running it

- `npm run dev` starts the backend and the dashboard.
- `npm run reset` rebuilds the database from `data/`: all 25 claims waiting.
- `npm run check` runs every check.

## Commit guard

`.claude/settings.json` and `.claude/hooks/guard-commit.mjs` stop Claude Code from committing with `--no-verify`, `git commit -n`, `LEFTHOOK=0` or `core.hooksPath`. Blocks go to `~/.claude/blocked-commits.log`, and every `git` command it sees goes to `~/.claude/guard-calls.log`.
