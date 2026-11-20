# Process

`uv sync` and `npm install` at the repo root install everything, including a git pre-commit hook. `npm run dev` starts the backend, the agent's service and the dashboard, and passes `.env` to the backend and the agent. `npm run reset` reseeds the database, on Supabase when `.env` has `DATABASE_URL`; stop `npm run dev` first.

`npm run check` runs every check:

- Python: ruff (lint and format), pyright, and pytest with 80% coverage
- TypeScript: ESLint, Prettier, tsc, and vitest with 80% coverage
- Playwright end-to-end tests, with a stand-in for the agent's service on port 8003

`npm run check` needs no `.env`: the tests use SQLite and a stub model, and never reach Supabase, Langfuse or OpenRouter.

The pre-commit hook runs the format, lint, type and unit test checks on every commit.

## Planning

When asked to plan, as in "Please plan the pilot", write the plan to `docs/PLAN.md` and write no code.

- Split the work into phases, usually 5 or 6, each building on the last.
- Give each phase detailed success criteria that you can verify yourself: tests that pass, commands and their output, API calls and their responses, and pages you check in the browser with the Playwright MCP server. Write each one as a checkbox.
- Give each phase at least one criterion on the code itself: which module each new piece goes in, under `docs/CODE_STANDARDS.md`. Behavior alone does not make code fit for a pull request.
- Then stop and wait until you are asked to implement the plan.

## Implementing

When asked to implement the plan, as in "Please implement the plan for the pilot", build every phase in order without stopping. For each phase:

1. Build it, with tests.
2. Check every success criterion and fix whatever fails.
3. Review the phase's diff against `docs/CODE_STANDARDS.md` as a reviewer would, and fix what it finds. Look for a second way to do something the code already does, a URL or client outside an API module, a tool outside `agent/tools.py`, harness code outside `agent/harness.py`, HTTP in the backend's rules, and scripted instructions.
4. Tick off its criteria in `docs/PLAN.md` and update `docs/STATUS.md`.
5. Commit. The pre-commit hook runs the checks; if it fails, fix the problem and commit again.

When the last phase is done, run `npm run check` and report the results.

## Rules

- Add tests with each change. Tests never call a model; use a stub model.
- Outside a plan, commit each change once you have checked it.
- Run `npm run check` before you hand work over.
- Before you hand work over, review the whole change against `docs/CODE_STANDARDS.md`. Passing checks show that the code works, not that it is well organized.
- When a review finds a structural problem that a test could catch, add it to `agent/tests/test_structure.py` or `backend/tests/test_structure.py`.
- Never use `git commit --no-verify`.
- Never lower a threshold, turn off a rule or exclude a file to get a green run. If a rule looks wrong, stop and ask.
- Keep `docs/STATUS.md` up to date.
- Never push.
- Before live runs with the real model, reseed once with `npm run reset`, and keep to the live runs the plan names, such as a dispatch at N=3 stopped partway, a dispatch at N=25 and the evaluations; a dispatch works the whole queue, so there is no smaller trial run.
- Don't open `data/evals/` unless you're asked to.
- Everything must work on Windows: write `package.json` scripts as `uv run` commands or `.mjs` files.
