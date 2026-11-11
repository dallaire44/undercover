import type { Step } from "./api";

/** The sections of the wording and the manual the agent read, by their first line. */
export function SectionsRead({ steps }: Readonly<{ steps: Step[] }>) {
  const reads = steps.filter((step) => step.kind === "read");
  return (
    <section className="panel" aria-labelledby="sections-title">
      <h2 id="sections-title">Sections read</h2>
      {reads.length === 0 ? (
        <p className="muted">None yet.</p>
      ) : (
        <ul>
          {reads.map((step) => (
            <li key={step.id}>{step.text.split("\n")[0]}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
