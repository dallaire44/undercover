# LinkedIn post skeleton, from PILOT.md

The facts are filled in; write each line in your own words, as Ed asks. Aim for about 1,800 characters in total (LinkedIn's limit is 3,000).

## 1. Hook: the first two lines, about 200 characters

This is all that shows before "...see more".

- Prompt: What surprised you most? What would you tell a friend in one breath?
- Facts you can use:
  - The plan was split into nine small parts, each proven before the next began.
  - Reviewing the plan is where you made the real decisions.
  - Zero code smells were found across every commit.

## 2. What it was: about 300 characters

- Prompt: In your words, what did you build, and why does it matter?
- Facts:
  - Week 1 Day 3 of Ed Donner's AI FDE course. You were the forward deployed engineer for UnderCover, a fictional travel insurer.
  - Claude Code built the pilot of its claims platform: an agent that approves, declines or refers each claim with a payout and a reason, plus a dashboard for the handlers.

## 3. The plan in small parts, and your review: about 450 characters

- Prompt: What did the structure of the plan, and reviewing it, teach you? Name one decision you agreed with or would have changed.
- Facts:
  - Nine phases, each with one goal, its own success criteria and one commit. When something broke, it broke in the phase that caused it.
  - The plan listed its decisions for your review. For example, the model never sees a customer's contact details.
  - Your three additions each went into the client's documents and a planned phase before "implement": dark mode, a color-blind mode with check, cross and arrow symbols, and Decision and Payout columns.

## 4. Two kinds of guardrail: automated and human, about 550 characters

- Prompt: What does each kind of guardrail protect, and why do you need both?
- Facts, automated (they guard code quality and whether the app meets its goals, and run before every commit):
  - Ruff with Pylint's refactor checks catches the code smells from Martin Fowler's *Refactoring*. None turned up, partly because the agent wrote within the limits.
  - pyright checks the types.
  - 44 Python, 31 dashboard and 12 browser tests check the app does what the spec asks.
- Facts, human (they guard what no rule can: judgment and accountability):
  - The agent can approve any claim, but a payout over $1,000 waits for a handler's sign-off, and the backend, not the prompt, enforces it.
  - When the agent tried to pay $3,750 itself, the backend refused until a handler signed off.
  - The agent referred 6 of the 25 claims to a handler for judgment.

## 5. Close: about 250 characters

- Prompt: A question for your network, in your words. For example, where do they put the human in their agent's loop?
- Thank @Ed Donner (type @ and pick him from the list) and name the course: AI FDE: The Forward Deployed Engineer & Agentic AI Architect.
- End with "Link to my build in the comments."

## 6. Hashtags

#ForwardDeployedEngineer #AgenticAI #ClaudeCode #HumanInTheLoop #CodeQuality

## Before posting

- Attach `community_contributions/david_dallaire/queue-dark-color-blind.png` as the image, with alt text (see `skeleton_linkedin_ex1.md`).
- Put https://github.com/dallaire44/undercover/tree/week1day3_FDE in the first comment.
- Use plain text only. No Markdown, and no Unicode "bold" letters, because screen readers garble them.
- Read it aloud. Any line that doesn't sound like you, rewrite.
- Check the length: under 3,000 characters, and about 1,800 is the target.
