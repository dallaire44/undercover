export const FIRST_AGENTS = 3;
const MOST_AGENTS = 25;

/** How many claim agents work at once: from 1 to 25. */
export function AgentsField({
  agents,
  onChange,
}: Readonly<{ agents: number; onChange: (agents: number) => void }>) {
  return (
    <label className="agents">
      Claim agents at once{" "}
      <input
        type="number"
        min={1}
        max={MOST_AGENTS}
        value={agents}
        onChange={(event) => {
          const chosen = Number(event.target.value);
          onChange(Math.min(MOST_AGENTS, Math.max(1, chosen)));
        }}
      />
    </label>
  );
}
