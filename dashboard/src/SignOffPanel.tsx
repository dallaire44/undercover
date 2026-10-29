import { useCallback, useState } from "react";
import { listHandlers, signOff, type ClaimDetail } from "./api";
import { money } from "./format";
import { useLoad } from "./useLoad";

export function SignOffPanel({
  claim,
  onSignedOff,
}: Readonly<{ claim: ClaimDetail; onSignedOff: () => void }>) {
  const { data: handlers } = useLoad(listHandlers);
  const [handlerId, setHandlerId] = useState("");
  const chosen = handlerId || handlers?.[0]?.handler_id;
  const submit = useCallback(() => {
    if (chosen) void signOff(claim.claim_id, chosen).then(onSignedOff);
  }, [claim.claim_id, chosen, onSignedOff]);

  if (claim.status !== "awaiting_sign_off" || !claim.decision) return null;
  return (
    <section className="panel on-hold" aria-labelledby="hold-title">
      <h2 id="hold-title">Payment on hold</h2>
      <p>
        The payout of{" "}
        <span className="num">{money(claim.decision.payout)}</span> needs a
        handler&apos;s sign-off before it is paid.
      </p>
      <label>
        Handler{" "}
        <select
          value={chosen ?? ""}
          onChange={(event) => {
            setHandlerId(event.target.value);
          }}
        >
          {handlers?.map((handler) => (
            <option key={handler.handler_id} value={handler.handler_id}>
              {handler.name}
            </option>
          ))}
        </select>
      </label>{" "}
      <button type="button" onClick={submit}>
        Sign off and pay
      </button>
    </section>
  );
}
