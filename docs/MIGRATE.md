# Migrate: the app on its own

This copies the UnderCover app built from `docs/PLAN.md` into its own directory, `../undercover-app`, as a fresh git repository. Nothing that doesn't contribute to the app goes with it.

## What is copied

- **The app:** `backend/`, `agent/`, `dashboard/` and `e2e/`.
- **The data the backend reads:** `data/claims.json`, `data/policies.json`, `data/customers.json`, `data/handlers.json`, `data/company.json` and `data/policy_wording.md`. These are the files named in `backend/db.py`, `backend/decisions.py` and `backend/main.py`.
- **The docs:** everything in `docs/` except this file: the spec, the tech stack, the code standards, the process, the brand, the status, the plan and the accessibility notes.
- **The configuration:** `package.json`, `package-lock.json`, `pyproject.toml`, `uv.lock`, `tsconfig.json`, `eslint.config.js`, `playwright.config.ts`, `lefthook.yml`, `.gitignore`, `.gitattributes`, `.python-version`, `.nvmrc` and `.npmrc`.
- **`.env`**, with the OpenRouter key. It is in `.gitignore`, so it is never committed.
- **`AGENTS.md`, trimmed** to the parts used to build the app: the context, the documents to read first (with `docs/ACCESSIBILITY.md` added), the agent's role, how a build goes and the folders.

## What is left out, and why

- **Course material:** `labs/`, `guides/`, `setup/`, `assets/`, `community_contributions/`, `monitor.py` (AWS spend), the course's `README.md`, and the course-only parts of `AGENTS.md`: the course overview, the build days, the labs, the branches, the guides and AWS.
- **`context/`:** data governance's files for a later build's context layer. The app doesn't use them.
- **The rest of `data/`:**
  - `evals/`, the handlers' decisions, which the agent must never see. Nothing in the pilot uses them.
  - `security/`, the prompt-injection claim, kept for security testing.
  - `claims_manual.md`. The spec says the agent works from the policy wording alone for now.
  - `knowledge.json`, `plans.json`, `policy_wording_short.md` and `data/README.md`.
- **Generated and local files:** `node_modules/`, `.venv/`, caches, coverage, test results, `undercover.db` and `e2e/e2e.db`. The copy starts with a fresh database of 25 waiting claims.
- **Lab-only Python packages.** `pyproject.toml` lists 26 packages for the course. The app imports `fastapi`, `uvicorn`, `httpx`, `langchain`, `langchain-openai` and `python-dotenv`, which bring Pydantic and LangChain Core with them. The copy keeps only these, plus the dev tools.

## Steps

Run these from the root of this repo, on Linux or macOS. The app must be committed first: `git archive` copies the committed versions.

1. Copy the files, keeping their paths:

   ```bash
   DEST=../undercover-app
   mkdir "$DEST"
   git archive HEAD -- backend agent dashboard e2e docs \
     data/claims.json data/policies.json data/customers.json data/handlers.json \
     data/company.json data/policy_wording.md \
     package.json package-lock.json pyproject.toml uv.lock tsconfig.json \
     eslint.config.js playwright.config.ts lefthook.yml .gitignore .gitattributes \
     .python-version .nvmrc .npmrc ':(exclude)docs/MIGRATE.md' | tar -x -C "$DEST"
   cp .env "$DEST/"
   ```

2. In `$DEST/pyproject.toml`:
   - Set `dependencies` to `fastapi`, `httpx`, `langchain`, `langchain-openai`, `python-dotenv` and `uvicorn`, at the versions this repo uses.
   - Keep the `dev` group (`pytest`, `pytest-cov`, `ruff`).
   - Remove the `server` group.
   - Leave the `[tool.*]` settings as they are.

   Then run `uv lock` in `$DEST`. It starts from the copied `uv.lock`, so it keeps the tested versions and drops the packages no longer needed.
3. Trim `$DEST/.gitignore` to what applies: secrets, Python, Node and Vite, Playwright, local databases and editors.
4. Write a short `$DEST/README.md`: what the app is, how to install, run and check it, and where the docs are. Write `$DEST/AGENTS.md` from this repo's `AGENTS.md`, keeping the context, "Start here" (adding `docs/ACCESSIBILITY.md`), "Your role in the build", how a build goes and the app's folders, and dropping everything about the course.
5. Set it up and prove it in `$DEST`:

   ```bash
   git init
   uv sync
   npm install
   npm run check
   git add -A
   git commit -m "UnderCover claims pilot"
   ```

   `npm install` installs the pre-commit hook, which needs the git repository, so `git init` comes first. The commit runs the hook's checks again.

## Checks

- `git ls-files` in `$DEST` lists 84 files, none of them under `labs/`, `guides/`, `setup/`, `assets/`, `context/` or `data/evals/`.
- `grep -r evals backend agent` in `$DEST` finds nothing.
- `npm run check` passes in `$DEST`: ruff, pyright, pytest, ESLint, Prettier, tsc, vitest and Playwright.
- With this repo's dev servers stopped, since both use ports 8000 and 5173, `npm run dev` in `$DEST` serves the dashboard with 25 waiting claims.
