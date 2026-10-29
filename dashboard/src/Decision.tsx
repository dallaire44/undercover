import type { ClaimDetail } from "./api";
import { VerdictChip } from "./Chips";
import { date, money } from "./format";

export function Decision({ claim }: Readonly<{ claim: ClaimDetail }>) {
  const { decision, payment, sign_off: signOff } = claim;
  if (!decision) return null;
  return (
    <section className="panel" aria-labelledby="decision-title">
      <h2 id="decision-title">Decision</h2>
      <p>
        <VerdictChip verdict={decision.decision} />{" "}
        <span className="num">Payout {money(decision.payout)}</span>
      </p>
      <p>{decision.reason}</p>
      <p className="muted">Policy section: {decision.policy_section}</p>
      {signOff && (
        <p>
          Signed off by {signOff.handler_name} on {date(signOff.signed_at)}.
        </p>
      )}
      {payment && (
        <p>
          Paid <span className="num">{money(payment.amount)}</span> on{" "}
          {date(payment.paid_at)}.
        </p>
      )}
    </section>
  );
}
