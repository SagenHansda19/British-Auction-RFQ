import { useEffect, useMemo, useState } from "react";

// server clock = browser clock + offset from the last response
export function useServerNow(serverTime) {
  const offset = useMemo(() => new Date(serverTime).getTime() - Date.now(), [serverTime]);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  return now + offset;
}

