# Example: the skeleton filled out

An example of `skeleton_linkedin.md` filled in, to show the shape and the length. Rewrite it in your own words before posting, as Ed asks: the opinions in it ("the secret ... wasn't the code", "glad to see", "kept it honest") are placeholders for yours. Everything between the two lines below is the post, in plain text, ready to paste.

---

The secret to building an AI claims agent with a coding agent wasn't the code. It was a plan split into nine small parts, each proven before the next began.

This week in Ed Donner's AI FDE course, I played forward deployed engineer for UnderCover, a fictional travel insurer. Claude Code built the pilot of its claims platform: an agent that approves, declines or refers each claim with a payout and a reason, and a dashboard for the claims handlers.

Each part had one goal, its own success criteria and one commit, so when something broke, it broke in the part that caused it. Before writing any code, Claude Code listed its decisions for me to review. One I was glad to see: the model never sees a customer's contact details. Then I added three phases of my own: dark mode, a color-blind mode with check, cross and arrow symbols, and decision and payout columns on the queue.

Two kinds of guardrail kept it honest. The automated ones guard code quality and whether the app meets its goals, and run before every commit: Ruff with Pylint's refactor checks for the code smells in Martin Fowler's Refactoring (none turned up), pyright for types, and 44 Python, 31 dashboard and 12 browser tests. The human one guards what no rule can: judgment and accountability. The agent can approve any claim, but a payout over $1,000 waits for a handler. When it tried to pay $3,750 itself, the backend refused until a handler signed off.

Where do you put the human in your agent's loop?

Thanks to @Ed Donner for AI FDE: The Forward Deployed Engineer & Agentic AI Architect. Link to my build in the comments.

#ForwardDeployedEngineer #AgenticAI #ClaudeCode #HumanInTheLoop #CodeQuality

---

First comment: https://github.com/dallaire44/undercover/tree/week1day3_FDE

Image: `community_contributions/david_dallaire/queue-dark-color-blind.png`. Attach it with the image button below the text box; LinkedIn shows it below the post text, not inside it. In the image editor, add this alt text, which screen readers read aloud:

> The UnderCover claims queue in dark mode with color-blind mode on: counts of claims by state, and a table whose Decision and Payout columns show Approved decisions marked with a check.

Check the preview before posting: the image is wide (1540 x 643), and the feed may show a smaller or trimmed version.
