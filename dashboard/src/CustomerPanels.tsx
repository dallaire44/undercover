import { useCallback } from "react";
import { api } from "./api";
import { Facts } from "./Facts";
import { date, humanize, money } from "./format";
import { useLoad } from "./useLoad";

export function PolicyPanel({ policyId }: Readonly<{ policyId: string }>) {
  const load = useCallback(() => api.getPolicy(policyId), [policyId]);
  const { data: policy } = useLoad(load);
  if (!policy) return null;
  const { trip } = policy;
  return (
    <section className="panel" aria-labelledby="policy-title">
      <h3 id="policy-title">The policy</h3>
      <Facts
        rows={[
          ["Policy", <span className="mono">{policy.policy_id}</span>],
          ["Plan", humanize(policy.plan)],
          [
            "Add-ons",
            policy.add_ons.length
              ? policy.add_ons.map(humanize).join(", ")
              : "None",
          ],
          ["Trip", trip.destination],
          ["Dates", `${date(trip.departs_on)} to ${date(trip.returns_on)}`],
          ["Trip cost", money(trip.trip_cost)],
          ["Travelers", policy.travelers.join(", ")],
        ]}
      />
    </section>
  );
}

export function HistoryPanel({ customerId }: Readonly<{ customerId: string }>) {
  const load = useCallback(() => api.getClaimHistory(customerId), [customerId]);
  const { data: history } = useLoad(load);
  if (!history) return null;
  return (
    <section className="panel" aria-labelledby="history-title">
      <h3 id="history-title">{history.name}'s earlier claims</h3>
      {history.previous_claims.length === 0 ? (
        <p className="muted">None.</p>
      ) : (
        <ul className="plain">
          {history.previous_claims.map((previous) => (
            <li key={previous.claim_id}>
              <span className="mono">{previous.claim_id}</span>{" "}
              {humanize(previous.claim_type)}, {date(previous.filed_on)}:{" "}
              {previous.summary}. {humanize(previous.outcome)},{" "}
              {money(previous.amount_paid)} paid.
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
