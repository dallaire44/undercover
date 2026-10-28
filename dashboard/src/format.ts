const dollars = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

const dates = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

/** Format an amount in US dollars, such as $1,250.00. */
export function money(amount: number): string {
  return dollars.format(amount);
}

/** Format an ISO date, such as 2026-06-24, as Jun 24, 2026. */
export function date(iso: string): string {
  return dates.format(new Date(iso));
}

/** Turn an API word, such as trip_delay, into Trip delay. */
export function humanize(word: string): string {
  const spaced = word.replaceAll("_", " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
