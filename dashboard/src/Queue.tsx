import { api } from "./api";
import type { ClaimSummary } from "./api";
import { StatusChip, VerdictChip } from "./Chips";
import { date, humanize, money } from "./format";
import { STATES } from "./states";
import { useLoad } from "./useLoad";

function Dash() {
  return <span className="muted">–</span>;
}

function ClaimRow({ claim }: Readonly<{ claim: ClaimSummary }>) {
  return (
    <tr>
      <td className="mono">
        <a href={`#/claims/${claim.claim_id}`}>{claim.claim_id}</a>
      </td>
      <td className="wrap">
        <div>{claim.customer_name}</div>
        <div className="muted">{claim.summary}</div>
      </td>
      <td>{humanize(claim.claim_type)}</td>
      <td>{date(claim.submitted_on)}</td>
      <td className="mono amount">{money(claim.amount_claimed)}</td>
      <td>
        <StatusChip status={claim.status} />
      </td>
      <td>
        {claim.decision ? <VerdictChip verdict={claim.decision} /> : <Dash />}
      </td>
      <td className="mono amount">
        {claim.payout === null ? <Dash /> : money(claim.payout)}
      </td>
    </tr>
  );
}

function Counts({ claims }: Readonly<{ claims: ClaimSummary[] }>) {
  return (
    <ul className="counts">
      {STATES.map(({ key, label }) => (
        <li key={key} className="panel count">
          <span className={`dot state-${key}`} aria-hidden="true" />
          <span className="mono number">
            {claims.filter((claim) => claim.status === key).length}
          </span>
          <span>{label}</span>
        </li>
      ))}
    </ul>
  );
}

export function Queue() {
  const { data: claims, error } = useLoad(api.listClaims);
  if (error) return <p role="alert">The queue could not be loaded.</p>;
  if (!claims) return <p>Loading the queue.</p>;
  return (
    <>
      <h2>The queue</h2>
      <Counts claims={claims} />
      <section className="panel">
        <table className="queue">
          <thead>
            <tr>
              <th scope="col">Claim</th>
              <th scope="col">Customer</th>
              <th scope="col">Type</th>
              <th scope="col">Submitted</th>
              <th scope="col" className="amount">
                Claimed
              </th>
              <th scope="col">Status</th>
              <th scope="col">Decision</th>
              <th scope="col" className="amount">
                Payout
              </th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <ClaimRow key={claim.claim_id} claim={claim} />
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
