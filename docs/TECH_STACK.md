# Tech stack

- `backend/`: FastAPI and SQLite. Every API operation has an `operation_id`, a one-line docstring and no optional inputs. Paying a claim is a separate operation that takes the amount.
- `agent/`: two agents built with LangChain's `create_agent` on OpenRouter, with no other agent framework. The queue agent's entry point `run_queue(run_id)` works a run; `work_claim(run_id, claim_id)` hands one claim to a fresh claim agent, `run(claim_id, thread_id)`. They reach claims, documents and their instructions only through the backend's API. LangChain middleware retries failed model calls (`ModelRetryMiddleware`) and stops a claim agent that loops (`ModelCallLimitMiddleware`). They use `deepseek/deepseek-v4.1-flash` with low reasoning effort by default, or the model in the environment variable `MODEL_NAME` if set, such as `openrouter/free`.
- `dashboard/`: React, Vite and TypeScript.
- `e2e/`: Playwright tests.
- `data/`: the business data the backend starts from. The agent never sees `data/evals/`, which holds the answer key.

Python 3.12 with uv, all in the root `pyproject.toml`. Node 26. The OpenRouter key is `OPENROUTER_API_KEY` in `.env`.
