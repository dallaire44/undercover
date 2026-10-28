import type { Claim } from "./api";
import { VerdictChip } from "./Chips";
import { Facts } from "./Facts";
import { money } from "./format";

export function DecisionPanel({ claim }: Readonly<{ claim: Claim }>) {
  const { decision } = claim;
  if (!decision) return null;
  return (
    <section className="panel" aria-labelledby="decision-title">
      <h3 id="decision-title">The agent's decision</h3>
      <Facts
        rows={[
          ["Decision", <VerdictChip key="d" verdict={decision.decision} />],
          ["Payout", <span className="mono">{money(decision.payout)}</span>],
          ["Policy section", decision.policy_section],
        ]}
      />
      <p>{decision.reason}</p>
    </section>
  );
}
