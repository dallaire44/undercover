"""Run the agent: `uv run -m agent 5` for up to five claims, or `CLM-1001` for one."""

import sys

from agent import cli

if __name__ == "__main__":
    print(cli.follow(cli.start(sys.argv[1])))
