import { useSyncExternalStore } from "react";

export type Route =
  { page: "queue" } | { page: "instructions" } | { page: "claim"; id: string };

/** Read a hash such as #/claims/CLM-1001 or #/instructions. Anything else is the queue. */
export function parse(hash: string): Route {
  if (hash === "#/instructions") return { page: "instructions" };
  const match = /^#\/claims\/([\w-]+)$/.exec(hash);
  return match?.[1] ? { page: "claim", id: match[1] } : { page: "queue" };
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => {
    window.removeEventListener("hashchange", onChange);
  };
}

export function useRoute(): Route {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash);
  return parse(hash);
}
