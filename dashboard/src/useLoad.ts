import { useEffect, useState } from "react";

interface Loaded<T> {
  data?: T;
  error?: Error;
}

/** Run a load function and report its data or its error. Pass a stable function. */
export function useLoad<T>(load: () => Promise<T>): Loaded<T> {
  const [state, setState] = useState<{ load: () => Promise<T> } & Loaded<T>>({
    load,
  });

  useEffect(() => {
    let current = true;
    load().then(
      (data) => {
        if (current) setState({ load, data });
      },
      (error: unknown) => {
        if (current) setState({ load, error: error as Error });
      },
    );
    return () => {
      current = false;
    };
  }, [load]);

  return state.load === load ? state : {};
}
