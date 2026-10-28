import { useCallback, useEffect, useState } from "react";

export const POLL_MS = 2000;

interface State<T> {
  load: () => Promise<T>;
  data?: T;
  error?: Error;
}

interface Loaded<T> {
  data?: T;
  error?: Error;
  reload: () => void;
}

function refresh<T>(
  load: () => Promise<T>,
  setState: (state: State<T>) => void,
  isLive: () => boolean,
): void {
  load().then(
    (data) => {
      if (isLive()) setState({ load, data });
    },
    (error: unknown) => {
      if (isLive()) setState({ load, error: error as Error });
    },
  );
}

/**
 * Run a load function and report its data or its error. Pass a stable function.
 * While shouldPoll says yes for the latest data, load again every two seconds.
 */
export function useLoad<T>(
  load: () => Promise<T>,
  shouldPoll?: (data: T) => boolean,
): Loaded<T> {
  const [state, setState] = useState<State<T>>({ load });
  const [reloads, setReloads] = useState(0);
  const current = state.load === load ? state : { load };
  const polling =
    current.data !== undefined && shouldPoll?.(current.data) === true;

  useEffect(() => {
    let live = true;
    refresh(load, setState, () => live);
    return () => {
      live = false;
    };
  }, [load, reloads]);

  useEffect(() => {
    if (!polling) return;
    let live = true;
    const timer = setInterval(() => {
      refresh(load, setState, () => live);
    }, POLL_MS);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [load, polling]);

  const reload = useCallback(() => {
    setReloads((n) => n + 1);
  }, []);
  return { data: current.data, error: current.error, reload };
}
