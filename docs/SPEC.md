# The claims platform

From the head of claims operations at UnderCover Travel Insurance.

## How claims work today

UnderCover sells travel insurance on three plans: Economy, Premium and First. Our three claims handlers work through a queue of claims by hand. For each claim, a handler reads the customer's story and documents and checks them against the policy and our policy wording. Then they approve the claim with a payout, decline it or refer it. A claim is referred when it needs someone's judgment or more information, as the claims manual explains.

## The pilot

We want an AI agent, the UnderCover Agent, to work the queue the way a handler does. A handler starts a dispatch, choosing N, the number of claim agents that work at once, from 1 to 25. The dispatch works every claim left in progress and every waiting claim, oldest submitted first, with up to N claims at once, each worked by a claim agent from a clean start. Code chooses the claims and keeps track of the dispatch, with no model, and when every claim is back the dispatch finishes with a summary built from our records. We can also run the agent on one named claim. Only one dispatch or evaluation runs at a time. For each claim it should:

- read the claim, the customer's policy and claim history, and find and read the sections of the policy wording and the claims manual it needs
- approve, decline or refer the claim
- work out the payout when it approves
- explain the decision in two or three sentences, along with the relevant section of the policy

It works out each payout with our payout rules. When it approves a payout over $1,000, it stops and waits for a handler, keeping everything it has worked out. As soon as a handler signs off on the dashboard, it picks the claim up from where it stopped and pays it, and the payment records who signed off and when. Between the sign-off and the payment the claim shows as in progress, and if the agent isn't running at that moment it picks the claim up the next time it runs. A handler can only sign off for now.

If the agent is stopped partway through a claim, by a crash, a restart or Ctrl-C, the dispatch shows as stopped, and the next dispatch carries the claim on from where it got to, which doesn't count as a new attempt. A claim that hits a rate limit or a timeout waits and carries on from where it got to, as the same attempt, and one still hitting them after its waits stays in progress for the next dispatch. A claim that fails with any other error goes back in the queue and the same dispatch tries it once more from a clean start; a claim that fails twice is left for a handler. One bad claim never stops a dispatch.

We record the tokens and the cost of each model call, and the time the agent spends working on each claim, which leaves out any wait for a sign-off, each with the dispatch or evaluation it happened in.

To see how well the agent does, a handler runs an evaluation: the agent works copies of a labelled set of claims, through the same dispatch, and its decisions are scored against our handlers' decisions. The sets are the 25 claims of the queue and a held-out set, each whole or just its five `tiny` claims. The copies never show in the queue and nobody signs them off; an approval held for sign-off counts as finished.

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
- The current dispatch on the queue page, where a handler chooses N and starts it: each of its claims and where it stands, its model cost and time, and when it finishes its summary from our records: how many claims were approved, declined and referred, each payout waiting for a sign-off, and each claim left for a handler or still in progress. A start that is refused says why, such as when the agent isn't running.
- A scoreboard, where a handler starts an evaluation and sees every evaluation, newest first, with its decision accuracy, accuracy (the payout within a dollar too), the cost of mistakes (a wrongful decline $1,500, a wrongful approval its payout, a needless referral $50, a wrong amount on a right approval the difference), the share of claims not referred, the model cost and time per claim, and the time for the whole run. A claim the agent didn't decide counts as a referral. Each evaluation opens to its claims, the handler's decision and payout beside the agent's, the misses easy to spot.
- Each claim in full, with the agent's decision and its reasons, and the sections of the wording and the manual the agent read.
- What the agent is doing on a claim while it works, step by step.
- The agent's instructions for working a claim, read only.
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