"""Run the agent on one claim: uv run -m agent CLM-1001."""

import sys
import uuid

from agent.main import run

print(run(sys.argv[1], uuid.uuid4().hex))
