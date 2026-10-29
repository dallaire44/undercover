import { useCallback, useEffect, useState } from "react";

const POLL_MS = 2000;

/**
 * Load data when `load` changes. Pass a stable function. While `pollWhile`
 * says yes for the data so far, load again every two seconds, and once more
 * when it stops.
 */
export function useLoad<T>(
  load: () => Promise<T>,
  pollWhile?: (data: T | undefined) => boolean,
) {
  const [data, setData] = useState<T>();
  const [failed, setFailed] = useState(false);

  const reload = useCallback(
    () =>
      load().then(
        (loaded) => {
          setData(loaded);
          setFailed(false);
        },
        () => {
          setFailed(true);
        },
      ),
    [load],
  );

  useEffect(() => {
    void reload();
  }, [reload]);

  const polling = pollWhile?.(data) ?? false;
  useEffect(() => {
    if (!polling) return;
    const timer = setInterval(() => void reload(), POLL_MS);
    return () => {
      clearInterval(timer);
      void reload();
    };
  }, [polling, reload]);

  return { data, failed, reload };
}
