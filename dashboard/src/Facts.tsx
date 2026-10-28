import type { ReactNode } from "react";

export function Facts({
  rows,
}: Readonly<{ rows: readonly (readonly [string, ReactNode])[] }>) {
  return (
    <dl className="facts">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
