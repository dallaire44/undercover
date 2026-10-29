import { useCallback } from "react";
import { getClaim, startAgent } from "./api";
import { StatusChip } from "./Chips";
import { Decision } from "./Decision";
import { date, money, titleCase } from "./format";
import { HistoryPanel, PolicyPanel } from "./Records";
import { SignOffPanel } from "./SignOffPanel";
import { Steps } from "./Steps";
import { useLoad } from "./useLoad";

export function Claim({ claimId }: Readonly<{ claimId: string }>) {
  const {
    data: claim,
    failed,
    reload,
  } = useLoad(
    useCallback(() => getClaim(claimId), [claimId]),
    (loaded) => loaded?.status === "in_progress",
  );
  if (failed) return <p>Claim {claimId} was not found.</p>;
  if (!claim) return <p className="muted">Loading</p>;
  return (
    <>
      <p>
        <a href="#/">Back to the queue</a>
      </p>
      <h1>
        <span className="num">{claim.claim_id}</span>{" "}
        <StatusChip state={claim.status} />
      </h1>
      {claim.status === "waiting" && (
        <p>
          <button
            type="button"
            onClick={() => void startAgent(claimId).then(reload, reload)}
          >
            Run the agent
          </button>
        </p>
      )}
      <section className="panel" aria-labelledby="summary-title">
        <h2 id="summary-title">{claim.summary}</h2>
        <dl>
          <dt>Customer</dt>
          <dd>{claim.customer_name}</dd>
          <dt>Type</dt>
          <dd>{titleCase(claim.claim_type)}</dd>
          <dt>Incident</dt>
          <dd>
            {date(claim.incident_date)}, {claim.incident_location}
          </dd>
          <dt>Submitted</dt>
          <dd>{date(claim.submitted_on)}</dd>
          <dt>Claimed</dt>
          <dd className="num">{money(claim.amount_claimed)}</dd>
        </dl>
      </section>
      <SignOffPanel claim={claim} onSignedOff={() => void reload()} />
      <Decision claim={claim} />
      <Steps claimId={claimId} working={claim.status === "in_progress"} />
      <section className="panel" aria-labelledby="story-title">
        <h2 id="story-title">Story</h2>
        <p>{claim.story}</p>
      </section>
      <section className="panel" aria-labelledby="items-title">
        <h2 id="items-title">Items</h2>
        <table>
          <tbody>
            {claim.items.map((item) => (
              <tr key={item.description}>
                <td>{item.description}</td>
                <td>{titleCase(item.category)}</td>
                <td className="num right">{money(item.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="panel" aria-labelledby="documents-title">
        <h2 id="documents-title">Documents</h2>
        {claim.documents.map((document) => (
          <article key={document.name}>
            <h3>{document.name}</h3>
            <p>{document.content}</p>
          </article>
        ))}
      </section>
      <PolicyPanel policyId={claim.policy_id} />
      <HistoryPanel customerId={claim.customer_id} />
    </>
  );
}
