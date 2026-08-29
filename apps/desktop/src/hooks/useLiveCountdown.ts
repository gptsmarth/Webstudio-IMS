import { useEffect, useState } from 'react';

/**
 * Ticks a server-provided countdown down locally, once per second, instead of
 * leaving it frozen at whatever value was last fetched until the next poll.
 * Resets to the fresh value (and restarts ticking) whenever `seconds` changes,
 * e.g. when the parent's periodic refetch brings in a new authoritative value.
 */
export function useLiveCountdown(seconds: number | null | undefined): number | null {
  const [remaining, setRemaining] = useState<number | null>(seconds ?? null);

  useEffect(() => {
    setRemaining(seconds ?? null);
    if (seconds == null || seconds <= 0) return;
    const timer = window.setInterval(() => {
      setRemaining((current) => (current == null ? null : Math.max(0, current - 1)));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [seconds]);

  return remaining;
}
