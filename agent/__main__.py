"""Run the agent on one claim: `uv run -m agent CLM-1001`."""

import sys
import uuid

from agent.main import run

if __name__ == "__main__":
    print(run(sys.argv[1], str(uuid.uuid4())))
