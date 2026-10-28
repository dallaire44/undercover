# Week 1 Day 3: redoing the pilot from its plan

Notes on undoing the pilot's code while keeping its plan, so the plan can be implemented again. Done on 2026-10-28.

## Why

The pilot was built on `week1day3-ed`, on top of `main`, which is Ed's skeleton. The goal was to rebuild it from the same plan: undo the code the plan produced, keep `docs/PLAN.md`, and ask Claude Code again to "Please implement the plan for the pilot".

The plan and the code were committed together, phase by phase, so no commit holds only the plan. `PLAN.md` changed only in two ways during the build: its success criteria were ticked, and phases 7 to 9 were added. So the current file is the complete plan.

## Decisions

- **A new branch,** `week1day3-redo`, made from `main`. `week1day3-ed` stays as it is, so the two builds can be compared afterwards.
- **Untick all 71 success criteria** in `PLAN.md`, and change nothing else. `PROCESS.md` has the agent tick each criterion once it's proven, so the rebuild starts from an honest state.

## What came across and what went back

**Brought across from `week1day3-ed`:** the plan, the requirements and the other work.

- `docs/PLAN.md`, then unticked
- `docs/SPEC.md`, with the additions behind phases 7 and 9
- `docs/ACCESSIBILITY.md`, the requirement behind phase 8
- `docs/MIGRATE.md` and `AGENTS.md`, from separate requests
- `community_contributions/david_dallaire/`, `skeleton_linkedin.md`, `skeleton_linkedin_ex1.md` and `labs/week1day2.ipynb`

**Left as `main` has them:** the plan's output.

- `backend/` (including `backend/instructions.md`), `agent/`, `dashboard/` and `e2e/`
- `package.json`, `playwright.config.ts`, `README.md` and `docs/STATUS.md`

## The steps

1. **Commit the pending notes on `week1day3-ed`.** Git won't switch branches with uncommitted changes, and `AGENTS.md` says to commit before switching. The commit was `75d9570`, "lefthook_dd.md: costs, CI, the format check, logs and two sequence diagrams". It's the only change made to `week1day3-ed`.
2. **Make the new branch from `main`:**

   ```bash
   git checkout -b week1day3-redo main
   ```

3. **Bring the plan, the requirements and the other work across:**

   ```bash
   git checkout week1day3-ed -- docs/PLAN.md docs/SPEC.md docs/ACCESSIBILITY.md docs/MIGRATE.md AGENTS.md labs/week1day2.ipynb skeleton_linkedin.md skeleton_linkedin_ex1.md community_contributions/david_dallaire
   ```

4. **Untick the criteria.** All 71 `[x]` in `PLAN.md` are checkbox lines, which was checked with grep first, so this changes nothing else:

   ```bash
   sed -i 's/^\( *- \)\[x\] /\1[ ] /' docs/PLAN.md
   ```

5. **Clear the old build's databases.** Both are gitignored SQLite files.
   - `undercover.db` holds the old build's agent decisions on the 25 claims, which would cost API spend to recreate. So it was moved aside instead of deleted, to `undercover.week1day3-ed.db`. The `*.db` rule in `.gitignore` still covers the new name.
   - `e2e/e2e.db` was deleted, because the end-to-end tests rebuild it on every run.
6. **Install the dependencies,** as `AGENTS.md` says to after a switch:

   ```bash
   uv sync
   npm install
   ```

7. **Verify, then commit.** The commit was `f72bd29`, "Start the pilot again from its plan". Lefthook skipped its jobs, because only docs were staged.

## Verification

| Check | Result |
|---|---|
| `backend`, `agent`, `dashboard`, `e2e`, `package.json`, `playwright.config.ts`, `README.md` and `docs/STATUS.md` match `main` | Identical |
| Files that differ from `main` | Only the 11 docs and notes files brought across |
| `PLAN.md` compared with `week1day3-ed` | 71 lines changed, each only from `[x]` to `[ ]`, and no `[x]` left |
| `week1day3-ed` | Unchanged apart from the commit in step 1 |
| `npm run check:python` on the skeleton | Passed: 4 tests, 97% coverage |
| `npm run check:ts` on the skeleton | Passed: 2 tests |
| `npm run e2e` on the skeleton | Couldn't start, because the ports were in use. See below. |

## The end-to-end tests and the port clash

The skeleton's Playwright config starts its backend on port 8000 and its dashboard on port 5173. Both ports were already taken by another app on this machine, in `/media/dd/HD1/MyMain/Trading/Production/DATA`. That app's uvicorn backend and Vite frontend had been running since 2026-10-27 at 18:13. `ss -ltnp` showed which processes held the ports.

This has nothing to do with the redo. The old build passed its end-to-end tests because its Phase 4 moved them to ports 8001 and 5174. The other app was left running.

It matters for the rebuild too. Phase 4 moves only the end-to-end tests, and two parts of the product stay on port 8000:

- `npm run dev` won't be able to start UnderCover's backend on port 8000.
- The agent looks for the backend at `http://localhost:8000` unless `BACKEND_URL` is set. So the plan's real-agent checks would call the DATA app instead of UnderCover.

So stop the DATA app while rebuilding.

## Next steps

1. Stop the DATA app, then run `npm run e2e` to confirm the skeleton is fully green.
2. Start a new Claude Code session at the repo root, on `week1day3-redo`, and ask: "Please implement the plan for the pilot". Six of the criteria run the real agent on the OpenRouter key, so the rebuild costs a little API spend, as it did the first time.
3. When it's done, compare the two builds:

   ```bash
   git diff week1day3-ed week1day3-redo
   ```

To go back to the original build at any time, commit any work first, then:

```bash
git checkout week1day3-ed
uv sync
npm install
```

To use the original build's database again, move `undercover.week1day3-ed.db` back to `undercover.db`.
