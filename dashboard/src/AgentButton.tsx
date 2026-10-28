import { useState } from "react";

export function AgentButton({
  label,
  start,
  onStarted,
}: Readonly<{
  label: string;
  start: () => Promise<unknown>;
  onStarted: () => void;
}>) {
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  const click = () => {
    setBusy(true);
    setError(undefined);
    void start()
      .then(onStarted, (problem: unknown) => {
        setError((problem as Error).message);
      })
      .finally(() => {
        setBusy(false);
      });
  };

  return (
    <div className="action">
      <button type="button" onClick={click} disabled={busy}>
        {label}
      </button>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
