# The claims pilot

From the head of claims operations at UnderCover Travel Insurance.

## How claims work today

UnderCover sells travel insurance on three plans: Economy, Premium and First. Our three claims handlers work through a queue of claims by hand. For each claim, a handler reads the customer's story and documents and checks them against the policy and our policy wording. Then they approve the claim with a payout, decline it or refer it. A claim is referred when it needs someone's judgment or more information, as the claims manual explains.

## The pilot

We want an AI agent, the UnderCover Agent, to work the queue the way a handler does. For each claim it should:

- read the claim, the customer's policy and claim history, and the policy wording
- approve, decline or refer the claim
- work out the payout when it approves
- explain the decision in two or three sentences, along with the relevant section of the policy

Our goal is to handle claims straight through, as accurately as our handlers do.

## What the team needs to see

- The queue, with where each claim stands: waiting, in progress, waiting for sign-off or decided. It is a table with these columns, in this order:
  - **Claim**: the claim's id, which opens the claim.
  - **Customer**: the customer's name, with the claim's one-line summary beneath it.
  - **Type**: the kind of claim.
  - **Submitted**: the date the claim was submitted.
  - **Claimed**: the amount claimed.
  - **Status**: waiting, in progress, waiting for sign-off or decided.
  - **Decision**: the agent's decision, approved, declined or referred. Empty until the agent has decided.
  - **Payout**: the payout the agent decided. A decline or a referral shows $0.00. Empty until the agent has decided.
- Each claim in full, with the agent's decision and its reasons.
- What the agent is doing on a claim while it works, step by step.
- The agent's instructions, read only.
- Light or dark screens, as each person prefers. The screens start in the computer's own setting, and a slider on every screen changes it and remembers the choice. The slider is a small track with a round dot: the dot at the left means the dark screens are off, and at the right means they are on. A screen reader announces it as a switch that is on or off, and it works from the keyboard.

## Rules

- A payout over $1,000 needs a handler's sign-off. The agent can approve such a claim, but the payment waits until a handler signs off. The system must block the payment until then, even if the agent tries to pay.
- Decisions follow the policy wording.
- Our handlers' own decisions on these claims are in `data/evals/`. We use them to check the agent's work. The agent must never see them.
- Amounts are in US dollars.

## Our records

Everything is in `data/`, described in `data/README.md`: the claims queue, the policies, the customers, the plans, the handlers, the policy wording and the claims manual. The held-out claims in `data/evals/` are for checking the agent later and stay out of the queue.

## Not for now

- The claims manual. For the pilot, the agent works from the policy wording alone.
- No sign-in. Everyone who uses the screens sees everything.
- No real payments.
- No messages to customers.