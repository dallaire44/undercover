import type { ClaimSummary, State } from "./api";
import { StatusChip, VerdictChip } from "./Chips";
import { date, money, STATES, titleCase } from "./format";

const ORDER: State[] = [
  "waiting",
  "in_progress",
  "awaiting_sign_off",
  "decided",
];

function Counts({ claims }: Readonly<{ claims: ClaimSummary[] }>) {
  return (
    <ul className="counts" aria-label="Claims by status">
      {ORDER.map((state) => (
        <li key={state} className="panel">
          <span className={`dot state-${state}`} aria-hidden="true" />
          <span>{STATES[state]}</span>
          <strong className="num">
            {claims.filter((claim) => claim.status === state).length}
          </strong>
        </li>
      ))}
    </ul>
  );
}

const Dash = () => <span className="muted">&mdash;</span>;

function Row({ claim }: Readonly<{ claim: ClaimSummary }>) {
  return (
    <tr>
      <td className="num">
        <a href={`#/claims/${claim.claim_id}`}>{claim.claim_id}</a>
      </td>
      <td>
        <div>{claim.customer_name}</div>
        <div className="muted">{claim.summary}</div>
      </td>
      <td>{titleCase(claim.claim_type)}</td>
      <td>{date(claim.submitted_on)}</td>
      <td className="num right">{money(claim.amount_claimed)}</td>
      <td>
        <StatusChip state={claim.status} />
      </td>
      <td>
        {claim.decision ? <VerdictChip verdict={claim.decision} /> : <Dash />}
      </td>
      <td className="num right">
        {claim.payout === null ? <Dash /> : money(claim.payout)}
      </td>
    </tr>
  );
}

const COLUMNS = [
  "Claim",
  "Customer",
  "Type",
  "Submitted",
  "Claimed",
  "Status",
  "Decision",
  "Payout",
];
const RIGHT = new Set(["Claimed", "Payout"]);

export function Queue({ claims }: Readonly<{ claims: ClaimSummary[] }>) {
  return (
    <>
      <h1>Claims queue</h1>
      <Counts claims={claims} />
      <div className="panel table-panel">
        <table>
          <thead>
            <tr>
              {COLUMNS.map((name) => (
                <th
                  key={name}
                  scope="col"
                  className={RIGHT.has(name) ? "right" : undefined}
                >
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <Row key={claim.claim_id} claim={claim} />
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
