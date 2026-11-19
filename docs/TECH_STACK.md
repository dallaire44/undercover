# Tech stack

- `backend/`: FastAPI on SQLAlchemy Core. With `DATABASE_URL` set it uses Supabase Postgres through the session pooler, with every table in the `undercover` schema (set as the connection's search path) and at most 4 connections; without it, as in the tests, SQLite. Each query is written once for both. Every API operation has an `operation_id`, a one-line docstring and no optional inputs. Paying a claim is a separate operation that takes the amount. The payout rules are `calculate_payout`, with the approval limit from `data/company.json`. `backend/agent_service.py` is the backend's only way to the agent.
- `agent/`: the UnderCover Agent on OpenRouter, in four parts. `agent/api.py` is its only way to the backend, `agent/tools.py` holds every tool, `agent/harness.py` holds the model, the claim agent's graph and the running of both agents, and `agent/service.py` is its entry point, a FastAPI service at `UNDERCOVER_AGENT` (or `http://127.0.0.1:8002`) that the backend calls to work runs and to resume a claim after a sign-off.
  - The queue agent is LangChain's `create_agent`, with middleware that hands refused calls back to the model and retries failed model calls (`ModelRetryMiddleware`).
  - The claim agent is a hand-written LangGraph graph (`StateGraph`, with no other agent framework). Its nodes take the place of middleware: the model node retries failed calls (`RetryPolicy`) and stops past 30 model calls, the tool node hands refused calls back to the model, a sign-off node waits on `interrupt()` when the backend holds a payout for sign-off, and a pay node pays.
  - Both agents are saved after every step by LangGraph's `PostgresSaver` (synchronous, `durability="sync"`) in the same Supabase database, or `InMemorySaver` without `DATABASE_URL`, so a claim carries on from its last step after a stop and resumes after a sign-off.
  - Each claim is traced in Langfuse, one session per attempt, named after the claim and its thread.
  - They reach claims, documents and their instructions only through the backend's API. They use `deepseek/deepseek-v4.1-flash` with low reasoning effort by default, or the model in the environment variable `MODEL_NAME` if set, such as `openrouter/free`.
- `dashboard/`: React, Vite and TypeScript.
- `e2e/`: Playwright tests, with a stand-in for the agent's service.
- `data/`: the business data the backend starts from. The agent never sees `data/evals/`, which holds the answer key.

Python 3.12 with uv, all in the root `pyproject.toml`. Node 26. The keys are in `.env`: `OPENROUTER_API_KEY`, `DATABASE_URL` (Supabase's session pooler) and `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_BASE_URL`. Nothing loads `.env` in code: `npm run dev` and `npm run reset` pass it, and the tests never see it.
