import { useEffect, useRef } from "react";

/**
 * Calls fn() once immediately, then every intervalMs while shouldPoll() is true.
 * fn returns whatever — we don't use the result. Designed for cases where fn
 * itself updates React state (e.g. refetching an audit and storing it).
 */
export function usePolling(
  fn: () => Promise<unknown> | unknown,
  intervalMs: number,
  shouldPoll: () => boolean,
) {
  const fnRef = useRef(fn);
  const shouldRef = useRef(shouldPoll);
  fnRef.current = fn;
  shouldRef.current = shouldPoll;

  useEffect(() => {
    let cancelled = false;

    async function tick() {
      if (cancelled) return;
      await fnRef.current();
      if (cancelled || !shouldRef.current()) return;
      timer = setTimeout(tick, intervalMs);
    }

    let timer: ReturnType<typeof setTimeout> = setTimeout(tick, 0);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [intervalMs]);
}
