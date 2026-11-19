import type { ClaimDetail } from "./api";
import { VerdictChip } from "./Chips";
import { dateTime, money } from "./format";

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
      {signOff && !payment && (
        <p>
          Signed off by {signOff.handler_name} on {dateTime(signOff.signed_at)}.
        </p>
      )}
      {payment && (
        <p>
          Paid <span className="num">{money(payment.amount)}</span> on{" "}
          {dateTime(payment.paid_at)}
          {payment.signed_off_by && `, signed off by ${payment.signed_off_by}`}.
        </p>
      )}
    </section>
  );
}
