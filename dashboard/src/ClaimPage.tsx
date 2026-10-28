import { useCallback } from "react";
import { AgentButton } from "./AgentButton";
import { api } from "./api";
import { StatusChip } from "./Chips";
import { HistoryPanel, PolicyPanel } from "./CustomerPanels";
import { DecisionPanel } from "./DecisionPanel";
import { Facts } from "./Facts";
import { date, humanize, money } from "./format";
import { PaymentPanel } from "./PaymentPanel";
import { Steps } from "./Steps";
import { useLoad } from "./useLoad";

export function ClaimPage({ id }: Readonly<{ id: string }>) {
  const load = useCallback(() => api.getClaim(id), [id]);
  const {
    data: claim,
    error,
    reload,
  } = useLoad(load, (c) => c.status === "in_progress");
  if (error) return <p role="alert">Claim {id} could not be loaded.</p>;
  if (!claim) return <p>Loading the claim.</p>;
  return (
    <>
      <p>
        <a href="#/">Back to the queue</a>
      </p>
      <section className="panel">
        <h2>
          <span className="mono">{claim.claim_id}</span>{" "}
          <StatusChip status={claim.status} />
        </h2>
        <p>{claim.summary}</p>
        <Facts
          rows={[
            ["Customer", claim.customer_name],
            ["Type", humanize(claim.claim_type)],
            ["Submitted", date(claim.submitted_on)],
            [
              "Incident",
              `${date(claim.incident_date)}, ${claim.incident_location}`,
            ],
            [
              "Claimed",
              <span className="mono">{money(claim.amount_claimed)}</span>,
            ],
          ]}
        />
      </section>
      {claim.status === "waiting" && (
        <AgentButton
          label="Run the agent"
          start={() => api.startAgent(id)}
          onStarted={reload}
        />
      )}
      <Steps claimId={id} active={claim.status === "in_progress"} />
      <DecisionPanel claim={claim} />
      <PaymentPanel claim={claim} onSignedOff={reload} />
      <section className="panel" aria-labelledby="story-title">
        <h3 id="story-title">The customer's story</h3>
        <p>{claim.story}</p>
      </section>
      <section className="panel" aria-labelledby="items-title">
        <h3 id="items-title">Items claimed</h3>
        <table className="queue">
          <thead>
            <tr>
              <th scope="col">Item</th>
              <th scope="col">Category</th>
              <th scope="col" className="amount">
                Amount
              </th>
            </tr>
          </thead>
          <tbody>
            {claim.items.map((item) => (
              <tr key={item.description}>
                <td>{item.description}</td>
                <td>{humanize(item.category)}</td>
                <td className="mono amount">{money(item.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="panel" aria-labelledby="documents-title">
        <h3 id="documents-title">Documents</h3>
        {claim.documents.map((document) => (
          <div key={document.name} className="document">
            <h4>
              {document.name}{" "}
              <span className="muted">({humanize(document.type)})</span>
            </h4>
            <p>{document.content}</p>
          </div>
        ))}
      </section>
      <PolicyPanel policyId={claim.policy_id} />
      <HistoryPanel customerId={claim.customer_id} />
    </>
  );
}
