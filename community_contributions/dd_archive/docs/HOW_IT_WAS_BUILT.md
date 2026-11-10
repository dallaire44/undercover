# How this repo was built

Reconstructed on 2026-11-03 from `git log` (78 commits on `week1day3-redo`), `guides/14_setting_up_a_project.md`, `docs/`, the config files and the notes in this folder. Where something is inferred and not stated in a source, it says so.

## The three layers

| Layer | When | Commits | What it added |
|---|---|---|---|
| 1. The course repo | 2026-09-19 to 10-14 | `aafb7b1` to `f2a10ec` | Labs, data, guides, `setup/`, README, `pyproject.toml` (uv, Python pinned to 3.12.12) |
| 2. The product scaffolding | 2026-09-26 | `85b14a9`, then small fixes | Everything the checks and the hook need, plus a skeleton product |
| 3. The pilot | 2026-10-28 | `f5ef173` to `a185d3c` on this branch | `backend/`, `agent/`, `dashboard/`, `e2e/` built from `docs/PLAN.md` |

Layers 1 and 2 are Ed's. Layer 3 is the build you directed, done twice: first on `week1day3-ed`, then redone on `week1day3-redo` from the same plan (see `week1day3-redo.md`).

## Layer 2: the scaffolding, step by step

`85b14a9` "Repo ready and documentation finalized for main build at w1d3" added 28 files in one commit. `lefthook.yml` has not changed since. Below is the order you would follow to make it from scratch. The order is inferred; `guides/14_setting_up_a_project.md` gives the same recipe.

### 1. Python with uv

```bash
uv init --bare --python 3.12
uv python pin 3.12.12
uv add fastapi uvicorn langchain ...        # runtime packages
uv add --dev ruff pytest pytest-cov         # dev group
```

The tool settings go in `pyproject.toml`:

- `[tool.ruff]` limited to `backend` and `agent`, with rules `E F W I B SIM UP PL S PT FAST C90 PLR1702`, McCabe complexity 10, and `S101` and `PLR2004` allowed in tests.
- `[tool.pytest.ini_options]` with `testpaths`, `--import-mode=importlib` and `--cov`.
- `[tool.coverage.report]` with `fail_under = 80`.
- `[tool.pyright]` pointing at `.venv`, Python 3.12.

### 2. Node

```bash
npm init -y
npm pkg set type=module
npm pkg set private=true --json
npm install react react-dom
npm install -D vite vitest typescript eslint prettier @playwright/test lefthook pyright concurrently ...
npm install -D -E typescript@6.0.3          # pinned: the newest typescript-eslint supports
```

Small files that go with it:

- `.nvmrc` holds `26`, and `.npmrc` holds `engine-strict=true`, with `engines` in `package.json` to match.
- `.gitattributes` holds `* text=auto eol=lf`. This came later, in `5e5a2b1`, so Prettier doesn't fail on Windows line endings.

### 3. The check scripts in `package.json`

| Script | Runs |
|---|---|
| `check:python` | `uv run ruff format --check && uv run ruff check && pyright && uv run pytest -q` |
| `check:ts` | `prettier --check` and `eslint` and `tsc` and `vitest run --root dashboard --coverage` |
| `e2e` | `playwright test` |
| `check` | all three, in that order |
| `format` | `ruff format` and `prettier --write` |
| `dev` | `concurrently` the backend (`uv run -m uvicorn ...`) and the dashboard (`vite dashboard`) |
| `prepare` | `lefthook install && playwright install chromium` |

`prepare` runs by itself after a plain `npm install`. That is how the git hook and Playwright's browser get set up for anyone who clones the repo. `reset` (`uv run -m backend.seed`) was added by pilot phase 1. `dev:backend` was changed to `uv run -m uvicorn` in `61237a4` for Windows Smart App Control.

### 4. The tool configs

- `eslint.config.js`: `strictTypeChecked` and `stylisticTypeChecked` from typescript-eslint, sonarjs, React hooks, jsx-a11y, Playwright and Vitest rules, and size limits (complexity 15, 500 lines per file, 200 per function, 5 parameters).
- `tsconfig.json`: strict, `noEmit`, covers `dashboard`, `e2e` and `playwright.config.ts`.
- `dashboard/vite.config.ts`: the React plugin, an `/api` proxy to the backend, jsdom for vitest, and an 80% statements threshold.
- `playwright.config.ts`: starts the backend and Vite for the end-to-end tests.

### 5. The pre-commit hook

Add lefthook with `npm install -D lefthook` (done in step 2). `lefthook.yml` defines two jobs under `pre-commit`, run in parallel:

| Job | Runs when staged files match | Steps (stop at the first failure) |
|---|---|---|
| `python` | `{backend,agent}/**/*.py` | `uv run ruff format {staged_files}`, re-stage; then `npm run check:python` |
| `typescript` | `{dashboard,e2e}/**` or `*.config.*` | `npx prettier --write -u {staged_files}`, re-stage; then `npm run check:ts` |

Playwright is not in the hook. It only runs in `npm run check`. A commit that touches neither kind of file, such as a docs edit, skips both jobs.

`npm install` runs `prepare`, which runs `lefthook install`. That writes `.git/hooks/pre-commit`, which git does not track, so a fresh clone needs `npm install` before the hook works. `lefthook_dd.md` has the full story, including cost and CI.

### 6. The skeleton product and the documents

The same commit added a hello-world product that already passes every check: `backend/main.py` (a health route), `agent/main.py`, `dashboard/src/App.tsx` and `e2e/health.spec.ts`, each with a test. It also added `docs/SPEC.md`, `docs/BRAND.md` and `docs/STATUS.md`, and changed `docs/PROCESS.md` and `AGENTS.md`. `docs/PROCESS.md` and `docs/TECH_STACK.md` first appeared in `ed1171f`, just before, and `docs/CODE_STANDARDS.md` in `c0058a0`, just after.

This is the harness idea from Week 1 Day 3: the guardrails are in place before the agent writes any code, and the agent works inside them.

## Layer 3: how the pilot was driven

The process is written in `AGENTS.md` and `docs/PROCESS.md`:

1. The agent reads the eight documents in `docs/` and `AGENTS.md`.
2. "Please plan the pilot" writes `docs/PLAN.md`: phases, each with checkbox success criteria. No code.
3. You review the plan.
4. "Please implement the plan for the pilot" builds every phase in order. Each phase is built with tests, every criterion is checked, the criteria are ticked in `PLAN.md`, `docs/STATUS.md` is updated, and the work is committed. The commit goes through lefthook, and a failure is fixed and committed again.
5. At the end, `npm run check` runs everything.

Rules that shaped the work: tests never call a model, never `--no-verify`, never lower a threshold or exclude a file to go green, never push.

## Layer 3: the phases on this branch

Each phase is one commit. File lists are from `git show --stat`.

| Phase | Commit | What it added |
|---|---|---|
| 0, the commit guard | `f5ef173` | `.claude/settings.json` and `.claude/hooks/guard-commit.mjs`, copied from `docs/CLAUDE_PRE_TOOL_USE_HOOK.md`. A PreToolUse hook on Bash that blocks `--no-verify`, `git commit -n`, `LEFTHOOK=0` and `core.hooksPath`. |
| 1, records and queue | `8e22a94` | `backend/db.py`, `models.py`, `records.py`, `seed.py`, `instructions.md`, the read routes, tests including an OpenAPI check. `reset` script. |
| 2, decisions and payments | `2e831a2` | `backend/rules.py` (decide, pay, sign off, the $1,000 rule), `steps.py`, tests for each rule. |
| 3, the agent | `f9d0140` | `agent/main.py`, `tools.py`, `api.py`, `__main__.py`; `backend/runner.py` for `start_agent` and `work_queue`; tests with a stub model. Two criteria ran the real model. |
| 4, queue and claim pages | `80b4caf` | `dashboard/src/` Queue, Claim, Decision, Records, Chips, `api.ts`, `format.ts`, `styles.css`; e2e specs for queue and claim; `playwright.config.ts` moved to ports 8001 and 5174. |
| 5, the agent at work | `f8b9f0b` | Steps timeline, sign-off panel, instructions page, polling in `useLoad.ts`; `e2e/agent-work.spec.ts`. |
| 6, handover | `3dadb26` | README note and `STATUS.md`. Real-model runs in the browser. |
| 7, light and dark slider | `4474b35` | `ThemeSwitch.tsx`, the start-up script in `index.html`, `data-theme` CSS, `e2e/theme.spec.ts`. |
| 8, color-blind mode | `2232fca` | `ModeSwitch.tsx` replaces `ThemeSwitch.tsx`; Okabe-Ito colors and chip symbols; `e2e/colors.spec.ts`. |
| 0 again | `a185d3c` | Tick the commit guard check. |

Phase 7 and 8 were added after the first six, when `SPEC.md` gained the light and dark slider and `docs/ACCESSIBILITY.md` was written. The first build also had a phase 9 (Decision and Payout columns, then sliders), which was dropped from the plan for the redo; the queue's Decision and Payout columns are now in the spec and in phase 4.

## What this document cannot tell you

- Ed's own steps when he made the scaffolding. The commit is one lump, so the order above is inferred from the guide.
- The installed versions at each moment. Only `uv.lock` and `package-lock.json` as they stand now are recorded.
- The prompts you typed, beyond the two quoted in `AGENTS.md` and `PROCESS.md`.
