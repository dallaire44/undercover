# Status

The pilot is being built in the phases of `docs/PLAN.md`. Built so far:

- `backend/`: FastAPI and SQLite. Phases 0 to 2: the records and the read operations (`list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `get_instructions`, `list_handlers`, `list_steps`), the write operations (`record_decision`, `pay_claim`, `sign_off`, `add_step`) with the payment rules in `backend/rules.py`, and the agent's instructions in `backend/instructions.md`. The database, `undercover.db` (or `UNDERCOVER_DB`), is seeded from `data/` on first use. `npm run reset` rebuilds it.
- `agent/`: the skeleton's entry point `run(claim_id, thread_id)`, with one tool that calls the health route.
- `dashboard/`: the skeleton's one page that shows whether the backend is up.
- `e2e/`: one test of that page.

## Commit guard

`.claude/settings.json` and `.claude/hooks/guard-commit.mjs` hold a Claude Code `PreToolUse` hook, from `docs/CLAUDE_PRE_TOOL_USE_HOOK.md`. It blocks Bash commands that would skip the pre-commit checks (`--no-verify`, `git commit -n`, `LEFTHOOK=0`, `core.hooksPath`) and logs each block to `~/.claude/blocked-commits.log`. Claude Code reads it from the folder where a session starts, so start sessions at the repo root.
