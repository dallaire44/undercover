import { useSyncExternalStore } from "react";

export type Route = { page: "queue" } | { page: "claim"; id: string };

/** Read a hash such as #/claims/CLM-1001. Anything else is the queue. */
export function parse(hash: string): Route {
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
