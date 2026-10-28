import type { Claim } from "./api";
import { VerdictChip } from "./Chips";
import { Facts } from "./Facts";
import { date, money } from "./format";

export function DecisionPanel({ claim }: Readonly<{ claim: Claim }>) {
  const { decision, payment, sign_off: signOff } = claim;
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
      {claim.status === "awaiting_sign_off" && (
        <p className="hold">
          Payment on hold: a payout over $1,000.00 needs a handler's sign-off.
        </p>
      )}
      {payment && (
        <p>
          Paid {money(payment.amount)} on {date(payment.paid_at)}.
        </p>
      )}
      {signOff && (
        <p>
          Signed off by {signOff.handler_name} on {date(signOff.signed_at)}.
        </p>
      )}
    </section>
  );
}
