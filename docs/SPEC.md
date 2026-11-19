# The claims platform

From the head of claims operations at UnderCover Travel Insurance.

## How claims work today

UnderCover sells travel insurance on three plans: Economy, Premium and First. Our three claims handlers work through a queue of claims by hand. For each claim, a handler reads the customer's story and documents and checks them against the policy and our policy wording. Then they approve the claim with a payout, decline it or refer it. A claim is referred when it needs someone's judgment or more information, as the claims manual explains.

## The pilot

We want an AI agent, the UnderCover Agent, to work the queue the way a handler does. We start it once and it works every waiting claim, choosing the order itself, then finishes with a short summary for the handlers. For trials we can cap a run at a number of claims, leaving the rest waiting, and we can also run it on one named claim. It plans its work as a to-do list and keeps it up to date, and it hands each claim to a helper that works that one claim from a clean start. For each claim it should:

- read the claim, the customer's policy and claim history, and find and read the sections of the policy wording and the claims manual it needs
- approve, decline or refer the claim
- work out the payout when it approves
- explain the decision in two or three sentences, along with the relevant section of the policy

It works out each payout with our payout rules. When it approves a payout over $1,000, it stops and waits for a handler, keeping everything it has worked out. As soon as a handler signs off on the dashboard, it picks the claim up from where it stopped and pays it, and the payment records who signed off and when. Between the sign-off and the payment the claim shows as in progress, and if the agent isn't running at that moment it picks the claim up the next time it runs. A handler can only sign off for now.

If the agent is stopped partway through a claim, by a crash, a restart or Ctrl-C, it carries on with that claim from where it got to the next time it runs, and that doesn't count as a new attempt. A claim that fails with an error goes back in the queue and starts afresh. A run that was stopped is finished the next time the agent runs.

Our goal is to handle claims straight through, as accurately as our handlers do.

## What the team needs to see

- The queue, with where each claim stands: waiting, in progress, waiting for sign-off, decided or needs a handler. It is a table with these columns, in this order:
  - **Claim**: the claim's id, which opens the claim.
  - **Customer**: the customer's name, with the claim's one-line summary beneath it.
  - **Type**: the kind of claim.
  - **Submitted**: the date the claim was submitted.
  - **Claimed**: the amount claimed.
  - **Status**: waiting, in progress, waiting for sign-off, decided or needs a handler.
  - **Decision**: the agent's decision, approved, declined or referred. Empty until the agent has decided.
  - **Payout**: the payout the agent decided. A decline or a referral shows $0.00. Empty until the agent has decided.
- The current run on the queue page: its cap, its to-do list with each item to do, in progress, done or left for a handler, and its summary when it finishes.
- Each claim in full, with the agent's decision and its reasons, and the sections of the wording and the manual the agent read.
- What the agent is doing on a claim while it works, step by step.
- The agent's instructions, read only: for running the queue and for working a claim.
- Light or dark screens, as each person prefers. The screens start in the computer's own setting, and a slider on every screen changes it and remembers the choice. The slider is a small track with a round dot: the dot at the left means the dark screens are off, and at the right means they are on. A screen reader announces it as a switch that is on or off, and it works from the keyboard.

## Rules

- A payout over $1,000 needs a handler's sign-off. The agent can approve such a claim, but the payment waits until a handler signs off. The system must block the payment until then, even if the agent tries to pay.
- Decisions follow the policy wording and the claims manual. The wording is the contract and comes first; the manual covers what the wording leaves open.
- Our handlers' own decisions on these claims are in `data/evals/`. We use them to check the agent's work. The agent must never see them.
- A run never works more claims than its cap.
- One bad claim never stops a run or leaves a claim stuck in progress. A claim that fails before it is finished goes back in the queue to be tried again, and a claim that fails twice is left for a handler. No claim is ever decided or paid twice. Before it finishes, a run checks that it has not missed a waiting claim within its cap.
- Amounts are in US dollars.

## Our records

Everything is in `data/`, described in `data/README.md`: the claims queue, the policies, the customers, the plans, the handlers, the policy wording and the claims manual. The held-out claims in `data/evals/` are for checking the agent later and stay out of the queue.

## Not for now

- No sign-in. Everyone who uses the screens sees everything.
- No real payments.
- No messages to customers.