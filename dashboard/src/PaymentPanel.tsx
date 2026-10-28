import { useState } from "react";
import { api } from "./api";
import type { Claim } from "./api";
import { date, money } from "./format";
import { useLoad } from "./useLoad";

function SignOffForm({
  claimId,
  onSignedOff,
}: Readonly<{ claimId: string; onSignedOff: () => void }>) {
  const { data: handlers = [] } = useLoad(api.listHandlers);
  const [chosen, setChosen] = useState<string>();
  const [error, setError] = useState<string>();
  const handlerId = chosen ?? handlers.at(0)?.handler_id ?? "";

  const signOff = () => {
    setError(undefined);
    void api
      .signOff(claimId, handlerId)
      .then(onSignedOff, (problem: unknown) => {
        setError((problem as Error).message);
      });
  };

  return (
    <div className="action">
      <label>
        Handler{" "}
        <select
          value={handlerId}
          onChange={(event) => {
            setChosen(event.target.value);
          }}
        >
          {handlers.map((handler) => (
            <option key={handler.handler_id} value={handler.handler_id}>
              {handler.name}
            </option>
          ))}
        </select>
      </label>{" "}
      <button type="button" onClick={signOff} disabled={!handlerId}>
        Sign off and pay
      </button>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}

export function PaymentPanel({
  claim,
  onSignedOff,
}: Readonly<{ claim: Claim; onSignedOff: () => void }>) {
  const { payment, sign_off: signOff } = claim;
  if (claim.status === "awaiting_sign_off") {
    return (
      <section className="panel" aria-labelledby="payment-title">
        <h3 id="payment-title">Payment</h3>
        <p className="hold">
          Payment on hold: a payout over $1,000.00 needs a handler's sign-off.
        </p>
        <SignOffForm claimId={claim.claim_id} onSignedOff={onSignedOff} />
      </section>
    );
  }
  if (!payment && !signOff) return null;
  return (
    <section className="panel" aria-labelledby="payment-title">
      <h3 id="payment-title">Payment</h3>
      {signOff && (
        <p>
          Signed off by {signOff.handler_name} on {date(signOff.signed_at)}.
        </p>
      )}
      {payment && (
        <p>
          Paid {money(payment.amount)} on {date(payment.paid_at)}.
        </p>
      )}
    </section>
  );
}
