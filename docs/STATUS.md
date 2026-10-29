# Status

The UnderCover claims pilot, built phase by phase from `docs/PLAN.md`.

## Built so far

- `backend/`: FastAPI and SQLite. On first start it copies the claims, policies, customers and handlers from `data/` into `undercover.db` (or the file named by `UNDERCOVER_DB`). Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `get_instructions` and `list_handlers`. The agent's instructions are in `backend/instructions.md`.
- `agent/`: still the hello-world agent.
- `dashboard/`: still one page that shows whether the backend is up.
- `e2e/`: one test of that page.

## Running it

- `npm run dev` starts the backend and the dashboard.
- `npm run reset` rebuilds the database from `data/`: all 25 claims waiting.
- `npm run check` runs every check.

## Commit guard

`.claude/settings.json` and `.claude/hooks/guard-commit.mjs` stop Claude Code from committing with `--no-verify`, `git commit -n`, `LEFTHOOK=0` or `core.hooksPath`. Blocks go to `~/.claude/blocked-commits.log`, and every `git` command it sees goes to `~/.claude/guard-calls.log`.
