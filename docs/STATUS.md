# Status

The pilot is being built in the phases of `docs/PLAN.md`. Built so far:

- `backend/`: FastAPI and SQLite. Phases 0 to 3: the records and the read operations (`list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `get_instructions`, `list_handlers`, `list_steps`), the write operations (`record_decision`, `pay_claim`, `sign_off`, `add_step`) with the payment rules in `backend/rules.py`, `start_agent` and `work_queue`, which run the agent in the background (`backend/runs.py`), and the agent's instructions in `backend/instructions.md`. The database, `undercover.db` (or `UNDERCOVER_DB`), is seeded from `data/` on first use. `npm run reset` rebuilds it.
- `agent/`: the UnderCover Agent, LangChain's `create_agent` with six tools that each call one backend operation. Its instructions come from `GET /api/instructions`, and each message, tool call and tool result is posted to the claim's steps. Run it on one claim with `uv run -m agent CLM-1001` (the backend must be running; `BACKEND_URL` defaults to `http://localhost:8000`). It uses `openai/gpt-6-luna`, or `MODEL_NAME` if set, with `OPENROUTER_API_KEY` from `.env`.
- `dashboard/`: the skeleton's one page that shows whether the backend is up.
- `e2e/`: one test of that page.

## Commit guard

`.claude/settings.json` and `.claude/hooks/guard-commit.mjs` hold a Claude Code `PreToolUse` hook, from `docs/CLAUDE_PRE_TOOL_USE_HOOK.md`. It blocks Bash commands that would skip the pre-commit checks (`--no-verify`, `git commit -n`, `LEFTHOOK=0`, `core.hooksPath`) and logs each block to `~/.claude/blocked-commits.log`. Claude Code reads it from the folder where a session starts, so start sessions at the repo root.
