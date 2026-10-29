import { useCallback } from "react";
import { getHistory, getPolicy } from "./api";
import { date, money, titleCase } from "./format";
import { useLoad } from "./useLoad";

export function PolicyPanel({ policyId }: Readonly<{ policyId: string }>) {
  const { data: policy } = useLoad(
    useCallback(() => getPolicy(policyId), [policyId]),
  );
  if (!policy) return null;
  return (
    <section className="panel" aria-labelledby="policy-title">
      <h2 id="policy-title">Policy</h2>
      <dl>
        <dt>Plan</dt>
        <dd>{policy.plan_name}</dd>
        <dt>Add-ons</dt>
        <dd>{policy.add_ons.length ? policy.add_ons.join(", ") : "None"}</dd>
        <dt>Trip</dt>
        <dd>
          {policy.trip.destination}, {date(policy.trip.departs_on)} to{" "}
          {date(policy.trip.returns_on)}
        </dd>
        <dt>Trip cost</dt>
        <dd className="num">{money(policy.trip.trip_cost)}</dd>
        <dt>Travelers</dt>
        <dd>{policy.travelers.join(", ")}</dd>
      </dl>
    </section>
  );
}

export function HistoryPanel({ customerId }: Readonly<{ customerId: string }>) {
  const { data: history } = useLoad(
    useCallback(() => getHistory(customerId), [customerId]),
  );
  if (!history) return null;
  return (
    <section className="panel" aria-labelledby="history-title">
      <h2 id="history-title">Claim history</h2>
      {history.previous_claims.length === 0 ? (
        <p className="muted">No earlier claims.</p>
      ) : (
        <ul>
          {history.previous_claims.map((earlier) => (
            <li key={earlier.claim_id}>
              <span className="num">{earlier.claim_id}</span>,{" "}
              {titleCase(earlier.claim_type)}, filed {date(earlier.filed_on)}:{" "}
              {earlier.outcome}, paid{" "}
              <span className="num">{money(earlier.amount_paid)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
