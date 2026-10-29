import { useEffect, useState } from "react";

/** Load data once per `load` function. Pass a stable function. */
export function useLoad<T>(load: () => Promise<T>) {
  const [data, setData] = useState<T>();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setData(undefined);
    setFailed(false);
    load().then(setData, () => {
      setFailed(true);
    });
  }, [load]);

  return { data, failed };
}
