# Status

A hello-world skeleton with every check in place:

- `backend/`: one route, `GET /api/health`
- `agent/`: the entry point `run(claim_id, thread_id)`, with one tool that calls the health route
- `dashboard/`: one page that shows whether the backend is up
- `e2e/`: one test of that page

Nothing of UnderCover is built yet. Update this file as you build.

## Commit guard

`.claude/settings.json` and `.claude/hooks/guard-commit.mjs` hold a Claude Code `PreToolUse` hook, from `docs/CLAUDE_PRE_TOOL_USE_HOOK.md`. It blocks Bash commands that would skip the pre-commit checks (`--no-verify`, `git commit -n`, `LEFTHOOK=0`, `core.hooksPath`) and logs each block to `~/.claude/blocked-commits.log`. Claude Code reads it from the folder where a session starts, so start sessions at the repo root.
